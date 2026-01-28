import com.opencsv.*;
import com.theokanning.openai.completion.chat.*;
import com.theokanning.openai.service.OpenAiService;



import java.io.*;
import java.nio.file.*;
import java.util.*;
import com.opencsv.exceptions.CsvValidationException;

public class JavaMethodNameSuggester {

    private static final String OPENAI_API_KEY = "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"; // Your key
    private static final int MAX_TOKENS = 16384;
    private static final int RESPONSE_TOKENS = 300;
    private static final int PROMPT_TOKENS = 100;

    public static void main(String[] args) throws IOException, CsvValidationException {
        String inputCsv = "/Users/durjoy/Documents/Lab CSSE/Result_files/Java/random_methods_java.csv";
        String outputCsv = "/Users/durjoy/Documents/Lab CSSE/Result_files/Java/gpt4o_suggestedMethodNames_java.csv";

        try (CSVReader reader = new CSVReader(new FileReader(inputCsv));
             CSVWriter writer = new CSVWriter(new FileWriter(outputCsv))) {

            String[] header = reader.readNext(); // skip header
            writer.writeNext(new String[]{
                    "Fully Qualified Name", "File Path", "Method Name",
                    "Method Body", "Context Tokens", "Context", "Suggested Names"
            });

            String[] row;
            while ((row = reader.readNext()) != null) {
                if (row.length < 4) continue;

                String fullyQualifiedName = row[0];
                String filePath = row[1];
                String methodName = row[2];
                String methodBody = row[3];

                System.out.println("🔍 Processing: " + fullyQualifiedName);

                String code = Files.readString(Paths.get(filePath));
                String context = extractContext(code, methodBody);
                int methodTokens = countTokens(methodBody);
                int availableTokens = MAX_TOKENS - methodTokens - RESPONSE_TOKENS - PROMPT_TOKENS;

                context = truncateContext(context, availableTokens);
                int contextTokens = countTokens(context);

                List<String> suggestions = callOpenAI(methodBody, context);
                writer.writeNext(new String[]{
                        fullyQualifiedName, filePath, methodName,
                        methodBody, String.valueOf(contextTokens),
                        context, String.join(", ", suggestions)
                });
            }
        }

        System.out.println("✅ Done");
    }

    private static String extractContext(String code, String methodBody) {
        int index = code.indexOf(methodBody);
        if (index == -1) return "";
        String before = code.substring(0, index);
        String after = code.substring(index + methodBody.length());
        return before + after;
    }

    private static int countTokens(String text) {
        // Approximate token count — use 4 chars/token as an estimate for GPT-4
        return (int) Math.ceil((double) text.length() / 4.0);
    }

    private static String truncateContext(String context, int maxTokens) {
        String[] words = context.split("\\s+");
        StringBuilder sb = new StringBuilder();
        int count = 0;
        for (String word : words) {
            count += Math.ceil(word.length() / 4.0);
            if (count > maxTokens) break;
            sb.append(word).append(" ");
        }
        return sb.toString().trim();
    }

    private static List<String> callOpenAI(String methodBody, String context) {
        OpenAiService service = new OpenAiService(OPENAI_API_KEY);

        String anonymizedBody = methodBody.replaceAll(
                "(public|protected|private)?\\s*(static\\s+)?[\\w<>\\[\\],]+\\s+\\w+\\s*\\(",
                "public void method_name("
        );

        String prompt = String.format("""
            Method body (with method name anonymized):
            %s

            Context from surrounding code:
            %s

            Provide method name suggestions as a numbered list, no explanations:
            """, anonymizedBody, context);

        ChatMessage system = new ChatMessage("system",
                "AI assistant that generates method names based on method body and context.");
        ChatMessage user = new ChatMessage("user", prompt);

        int retries = 0;
        while (retries < 5) {
            try {
                ChatCompletionRequest request = ChatCompletionRequest.builder()
                        .model("gpt-4o")
                        .messages(List.of(system, user))
                        .temperature(0.5)
                        .maxTokens(RESPONSE_TOKENS)
                        .build();

                ChatCompletionResult result = service.createChatCompletion(request);
                String content = result.getChoices().get(0).getMessage().getContent();
                return Arrays.asList(content.split("\n"));

            } catch (Exception e) {
                int wait = 20 * (retries + 1);
                System.err.println("⚠️ Rate limit or error, retrying after " + wait + "s");
                try {
                    Thread.sleep(wait * 1000L);
                } catch (InterruptedException ignored) {}
                retries++;
            }
        }

        System.err.println("❌ Failed after retries");
        return List.of("N/A");
    }
}

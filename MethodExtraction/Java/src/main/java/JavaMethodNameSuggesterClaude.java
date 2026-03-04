import java.io.*;
import java.net.URI;
import java.net.http.*;
import java.net.http.HttpRequest.BodyPublishers;
import java.net.http.HttpResponse.BodyHandlers;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;
import com.opencsv.*;
import com.opencsv.exceptions.CsvValidationException;
import com.google.gson.*;

public class JavaMethodNameSuggesterClaude {

    // Load Claude API key from environment (.env or shell)
    private static final String CLAUDE_API_KEY = System.getenv("ANTHROPIC_API_KEY");
    private static final int RESPONSE_TOKENS = 300;
    private static final HttpClient httpClient = HttpClient.newHttpClient();

    public static void main(String[] args) throws IOException, CsvValidationException {
        String inputCsv = "/Users/durjoy/Documents/Lab CSSE/Result_files/Java/random_methods_java.csv";
        String outputCsv = "/Users/durjoy/Documents/Lab CSSE/Result_files/Java/claude_suggestedMethodNames_java.csv";

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

                // Count tokens approx or just length / 4 (you can improve later)
                int contextTokens = countTokens(context);

                // Anonymize method name in method body
                String anonymizedBody = anonymizeMethodName(methodBody);

                // Call Claude API to get suggestions
                List<String> suggestions = callClaudeApi(anonymizedBody, context);

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
        return (int) Math.ceil((double) text.length() / 4.0);
    }

    private static String anonymizeMethodName(String methodBody) {
        return methodBody.replaceFirst(
                "(public|protected|private)?\\s*(static\\s+)?[\\w<>\\[\\],]+\\s+\\w+\\s*\\(",
                "public void method_name("
        );
    }

    private static List<String> callClaudeApi(String methodBody, String context) {
        if (CLAUDE_API_KEY == null || CLAUDE_API_KEY.isEmpty()) {
            throw new IllegalStateException("ANTHROPIC_API_KEY is not set. Please configure it in your environment or .env loader.");
        }
        try {
            String prompt = String.format("""
                Method body (with method name anonymized):
                %s

                Context from surrounding code:
                %s

                Provide method name suggestions as a numbered list, no explanations:
                """, methodBody, context);

            // Claude API expects JSON with fields: model, messages, temperature, max_tokens
            // Messages: list of { role, content } - but Claude expects "system" and "user"
            // We'll build JSON body accordingly

            JsonObject systemMessage = new JsonObject();
            systemMessage.addProperty("role", "system");
            systemMessage.addProperty("content", "AI assistant that provides only method name suggestions in a numbered list format.");

            JsonObject userMessage = new JsonObject();
            userMessage.addProperty("role", "user");
            userMessage.addProperty("content", prompt);

            JsonArray messages = new JsonArray();
            messages.add(systemMessage);
            messages.add(userMessage);

            JsonObject requestBody = new JsonObject();
            requestBody.addProperty("model", "claude-3-7-sonnet-20250219");
            requestBody.add("messages", messages);
            requestBody.addProperty("temperature", 0.5);
            requestBody.addProperty("max_tokens_to_sample", RESPONSE_TOKENS);

            String jsonBody = new Gson().toJson(requestBody);

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create("https://api.anthropic.com/v1/chat/completions"))
                    .header("Content-Type", "application/json")
                    .header("x-api-key", CLAUDE_API_KEY)
                    .POST(BodyPublishers.ofString(jsonBody))
                    .build();

            HttpResponse<String> response = httpClient.send(request, BodyHandlers.ofString());

            if (response.statusCode() != 200) {
                System.err.println("API call failed with status: " + response.statusCode());
                System.err.println("Response: " + response.body());
                return List.of("N/A");
            }

            JsonObject jsonResponse = JsonParser.parseString(response.body()).getAsJsonObject();
            String content = jsonResponse
                    .getAsJsonArray("choices")
                    .get(0)
                    .getAsJsonObject()
                    .get("message")
                    .getAsJsonObject()
                    .get("content")
                    .getAsString();

            // Split by newline into numbered suggestions
            String[] lines = content.strip().split("\n");
            List<String> suggestions = new ArrayList<>();
            for (String line : lines) {
                // Optional: remove numbering prefixes like "1. ", "2) ", etc.
                suggestions.add(line.replaceAll("^\\s*\\d+\\s*[.)]\\s*", "").trim());
            }
            return suggestions;

        } catch (Exception e) {
            System.err.println("Error calling Claude API: " + e.getMessage());
            return List.of("N/A");
        }
    }
}

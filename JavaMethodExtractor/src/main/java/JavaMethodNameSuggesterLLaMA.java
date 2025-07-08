import java.io.*;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.*;
import java.util.*;
import com.opencsv.*;
import com.google.gson.*;
import com.opencsv.exceptions.CsvValidationException;

public class JavaMethodNameSuggesterLLaMA {

    private static final String LLAMA_API_KEY = "0a62aec484719004430f8b114eab5bee96b89be9b33b975b3da5b8afbea6af49";
    private static final int RESPONSE_TOKENS = 300;
    private static final int MAX_TOKENS = 8192;
    private static final HttpClient httpClient = HttpClient.newHttpClient();

    public static void main(String[] args) throws IOException, CsvValidationException {
        String inputCsv = "/Users/durjoy/Documents/Lab CSSE/Result_files/Java/random_methods_java.csv";
        String outputCsv = "/Users/durjoy/Documents/Lab CSSE/Result_files/Java/llama_suggestedMethodNames_java.csv";

        try (CSVReader reader = new CSVReader(new FileReader(inputCsv));
             CSVWriter writer = new CSVWriter(new FileWriter(outputCsv))) {

            String[] header = reader.readNext(); // Skip header
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
                int contextTokens = countTokens(context);

                String anonymizedBody = anonymizeMethodName(methodBody);
                List<String> suggestions = callLlamaApiWithRetry(anonymizedBody, context);

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

    private static List<String> callLlamaApiWithRetry(String methodBody, String context) {
        String prompt = String.format("""
            Method body (with method name anonymized):
            %s

            Context from surrounding code:
            %s

            Provide method name suggestions as a numbered list, no explanations:
            """, methodBody, context);

        String endpoint = "https://api.together.xyz/v1/chat/completions";
        int maxRetries = 5;

        for (int attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                JsonObject systemMessage = new JsonObject();
                systemMessage.addProperty("role", "system");
                systemMessage.addProperty("content", "AI assistant that generates method names based on method body and context.");

                JsonObject userMessage = new JsonObject();
                userMessage.addProperty("role", "user");
                userMessage.addProperty("content", prompt);

                JsonArray messages = new JsonArray();
                messages.add(systemMessage);
                messages.add(userMessage);

                JsonObject requestBody = new JsonObject();
                requestBody.addProperty("model", "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8");
                requestBody.add("messages", messages);
                requestBody.addProperty("temperature", 0.5);
                requestBody.addProperty("max_tokens", RESPONSE_TOKENS);

                String jsonBody = new Gson().toJson(requestBody);

                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(endpoint))
                        .header("Content-Type", "application/json")
                        .header("Authorization", "Bearer " + LLAMA_API_KEY)
                        .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                        .build();

                HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

                if (response.statusCode() == 200) {
                    JsonObject json = JsonParser.parseString(response.body()).getAsJsonObject();
                    String content = json.getAsJsonArray("choices")
                            .get(0).getAsJsonObject()
                            .get("message").getAsJsonObject()
                            .get("content").getAsString();

                    return Arrays.stream(content.strip().split("\n"))
                            .map(line -> line.replaceAll("^\\s*\\d+[.)]?\\s*", "").trim())
                            .filter(line -> !line.isEmpty() && !line.toLowerCase().startsWith("based on"))
                            .toList();

                } else if (response.statusCode() == 429 || response.statusCode() == 503) {
                    int waitTime = 10 * attempt;
                    System.out.printf("⚠️ API call failed (status %d), retrying in %d seconds...\n", response.statusCode(), waitTime);
                    Thread.sleep(waitTime * 1000L);
                } else {
                    System.err.println("❌ API call failed: " + response.statusCode());
                    System.err.println(response.body());
                    break;
                }

            } catch (Exception e) {
                System.err.printf("❌ Exception during LLaMA API call (attempt %d): %s\n", attempt, e.getMessage());
                try {
                    Thread.sleep(10 * attempt * 1000L);
                } catch (InterruptedException ignored) {}
            }
        }

        return List.of("API_ERROR");
    }
}

import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.tree.*;
import java.io.*;
import java.util.*;
import java.util.stream.*;
import java.nio.file.*;
import java.util.regex.*;
import java.nio.charset.StandardCharsets;
import antlr.gen.Java20Lexer;
import antlr.gen.Java20Parser;
import antlr.gen.Java20ParserBaseListener;

public class JavaMethodExtractor {

    static class MethodInfo {
        String fullyQualifiedName;
        String filePath;
        String methodName;
        String methodBody;
        int lineCount;

        public String[] toCSVRow() {
            return new String[]{fullyQualifiedName, filePath, methodName, methodBody, String.valueOf(lineCount)};
        }
    }

    static final int TARGET_LINES = 50;
    static final int VARIANCE = 20;
    static final int MAX_RESULTS = 20;

    public static void main(String[] args) throws IOException {
        List<String> sourceRoots = Arrays.asList(
                "/Users/durjoy/Documents/Lab CSSE/Github_repos/Java/java-design-patterns",
                "/Users/durjoy/Documents/Lab CSSE/Github_repos/Java/spring-boot"
//                "/Users/durjoy/Documents/Lab CSSE/Github_repos/Java/spring-framework"
        );
        String outputCsv = "/Users/durjoy/Documents/Lab CSSE/Result_files/Java/random_methods_java.csv";

        List<MethodInfo> allMethods = new ArrayList<>();
        for (String root : sourceRoots) {
            Files.walk(Paths.get(root))
                    .filter(p -> p.toString().endsWith(".java"))
                    .forEach(p -> {
                        try {
                            System.out.println("Processing file: " + p.toString());
                            allMethods.addAll(extractMethodsFromFile(p.toFile()));
                        } catch (Exception e) {
                            System.err.println("Skipping file due to parse error: " + p);
                            // Optionally, print the error message for debugging
                            // e.printStackTrace();
                        }
                    });
        }

        List<MethodInfo> filtered = allMethods.stream()
                .filter(m -> m.lineCount >= 15 && m.lineCount <= 70)
                .collect(Collectors.toList());

        Collections.shuffle(filtered);
        List<MethodInfo> selected = filtered.stream().limit(MAX_RESULTS).collect(Collectors.toList());

        writeCSV(outputCsv, selected);
        System.out.println("✅ CSV written to: " + outputCsv);
    }

    private static List<MethodInfo> extractMethodsFromFile(File file) throws Exception {
        List<MethodInfo> methods = new ArrayList<>();
        String code = Files.readString(file.toPath());

        CharStream input = CharStreams.fromString(code);
        Java20Lexer lexer = new Java20Lexer(input);
        lexer.removeErrorListeners();
        lexer.addErrorListener(SilentErrorListener.INSTANCE);

        CommonTokenStream tokens = new CommonTokenStream(lexer);
        Java20Parser parser = new Java20Parser(tokens);
        parser.removeErrorListeners();
        parser.addErrorListener(SilentErrorListener.INSTANCE);

        ParseTree tree = parser.compilationUnit();
        ParseTreeWalker walker = new ParseTreeWalker();
        JavaMethodListener listener = new JavaMethodListener(file.getPath(), tokens, methods, code);
        walker.walk((ParseTreeListener) listener, tree);

        return methods;
    }

    private static void writeCSV(String filePath, List<MethodInfo> methods) throws IOException {
        try (BufferedWriter writer = Files.newBufferedWriter(Paths.get(filePath), StandardCharsets.UTF_8)) {
            writer.write("Fully Qualified Name,File Path,Method Name,Method Body,Line Count\n");
            for (MethodInfo m : methods) {
                writer.write(String.join(",", Arrays.stream(m.toCSVRow())
                        .map(s -> "\"" + s.replace("\"", "\"\"") + "\"").toArray(String[]::new)));
                writer.write("\n");
            }
        }
    }

    static class JavaMethodListener extends Java20ParserBaseListener {
        private final String filePath;
        private final CommonTokenStream tokens;
        private final List<MethodInfo> methods;
        private final String code;

        public JavaMethodListener(String filePath, CommonTokenStream tokens, List<MethodInfo> methods, String code) {
            this.filePath = filePath;
            this.tokens = tokens;
            this.methods = methods;
            this.code = code;
        }

        @Override
        public void enterMethodDeclaration(Java20Parser.MethodDeclarationContext ctx) {
            try {
                String methodName = ctx.methodHeader().methodDeclarator().getChild(0).getText();
                if (methodName.toLowerCase().contains("test")) return;

                System.out.println("methodDeclarator: " + ctx.methodHeader().methodDeclarator().getText());
                System.out.println("methodName: " + methodName);

                Token start = ctx.getStart();
                Token stop = ctx.getStop();
                int startIdx = start.getStartIndex();
                int stopIdx = stop.getStopIndex();
                String methodText = code.substring(startIdx, stopIdx + 1);
                int lineCount = countCodeLines(methodText);

                if (lineCount > 1) {
                    MethodInfo info = new MethodInfo();
                    info.fullyQualifiedName = filePath + "::" + methodName;
                    info.filePath = filePath;
                    info.methodName = methodName;
                    info.methodBody = methodText;
                    info.lineCount = lineCount;
                    methods.add(info);
                    System.out.println("Found method: " + methodName + " in " + filePath + " with " + lineCount + " lines");
                }
            } catch (Exception e) {
                System.err.println("Error extracting method: " + e.getMessage());
            }
        }

        private int countCodeLines(String code) {
            int count = 0;
            boolean inBlock = false;
            for (String line : code.split("\n")) {
                String stripped = line.trim();
                if (stripped.isEmpty()) continue;

                if (inBlock) {
                    if (stripped.contains("*/")) inBlock = false;
                    continue;
                }

                if (stripped.startsWith("/*")) {
                    inBlock = true;
                    continue;
                }
                if (stripped.startsWith("//")) continue;

                count++;
            }
            return count;
        }
    }

    public static class SilentErrorListener extends BaseErrorListener {
        public static final SilentErrorListener INSTANCE = new SilentErrorListener();

        @Override
        public void syntaxError(Recognizer<?, ?> recognizer,
                                Object offendingSymbol,
                                int line, int charPositionInLine,
                                String msg, RecognitionException e) {
            // Do nothing (suppress error)
        }
    }
}

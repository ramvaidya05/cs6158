package lab;

import com.fasterxml.jackson.databind.JsonNode;
import org.apache.commons.csv.*;
import java.io.*;
import java.util.*;

/** Scoped, evaluator-owned CSV oracle; no generated code or external I/O. */
public final class CsvScenario {
    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalArgumentException(message);
    }
    private static Character character(JsonNode value) {
        if (value.isNull()) return null;
        require(value.isTextual() && value.asText().length() == 1, "One UTF-16 character required");
        return value.asText().charAt(0);
    }
    private static CSVFormat format(JsonNode config) {
        CSVFormat.Builder builder = CSVFormat.DEFAULT.builder();
        if (config == null) return builder.build();
        require(config.isObject(), "Config must be an object");
        config.fields().forEachRemaining(entry -> {
            JsonNode value = entry.getValue();
            switch (entry.getKey()) {
                case "delimiter" -> { Character c = character(value); require(c != null, "Delimiter cannot be null"); builder.setDelimiter(c); }
                case "quote" -> builder.setQuote(character(value));
                case "escape" -> builder.setEscape(character(value));
                case "record_separator" -> { require(value.isTextual(), "Record separator must be text"); builder.setRecordSeparator(value.asText()); }
                case "null_string" -> { require(value.isTextual() || value.isNull(), "Null marker must be text/null"); builder.setNullString(value.isNull() ? null : value.asText()); }
                case "quote_mode" -> { require(value.isTextual(), "Quote mode must be text"); builder.setQuoteMode(QuoteMode.valueOf(value.asText())); }
                case "ignore_empty_lines", "ignore_surrounding_spaces", "trim" -> {
                    require(value.isBoolean(), "Boolean option required");
                    switch (entry.getKey()) {
                        case "ignore_empty_lines" -> builder.setIgnoreEmptyLines(value.asBoolean());
                        case "ignore_surrounding_spaces" -> builder.setIgnoreSurroundingSpaces(value.asBoolean());
                        default -> builder.setTrim(value.asBoolean());
                    }
                }
                default -> throw new IllegalArgumentException("Unsupported CSV setting");
            }
        });
        return builder.build();
    }
    public static Map<String, Object> run(JsonNode input) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", input.path("id").asText());
        try {
            CSVFormat format = format(input.get("config"));
            Object value;
            switch (input.path("operation").asText()) {
                case "parse" -> {
                    require(input.has("text") && input.get("text").isTextual(), "Text input required");
                    try (CSVParser parser = CSVParser.parse(input.get("text").asText(), format)) {
                        List<List<String>> rows = new ArrayList<>();
                        for (CSVRecord record : parser.getRecords()) rows.add(record.toList());
                        value = rows;
                    }
                }
                case "print" -> {
                    require(input.has("records") && input.get("records").isArray(), "Records array required");
                    StringBuilder output = new StringBuilder();
                    try (CSVPrinter printer = new CSVPrinter(output, format)) {
                        for (JsonNode row : input.get("records")) {
                            require(row.isArray(), "Record array required");
                            List<String> fields = new ArrayList<>();
                            for (JsonNode cell : row) {
                                require(cell.isNull() || cell.isTextual(), "Only text/null fields are admitted");
                                fields.add(cell.isNull() ? null : cell.asText());
                            }
                            printer.printRecord(fields);
                        }
                    }
                    value = output.toString();
                }
                default -> throw new IllegalArgumentException("Unsupported CSV operation");
            }
            result.put("status", "ok"); result.put("value", value);
        } catch (IOException | UncheckedIOException exception) {
            result.put("status", "exception"); result.put("type", "CSVParseError");
        } catch (IllegalArgumentException exception) {
            result.put("status", "exception"); result.put("type", "IllegalArgumentException");
        }
        return result;
    }
}

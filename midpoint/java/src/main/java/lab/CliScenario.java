package lab;

import com.fasterxml.jackson.databind.JsonNode;
import org.apache.commons.cli.*;
import java.util.*;

/** Explicit scoped dispatch: no reflection and no candidate code in the oracle. */
public final class CliScenario {
    private static String[] strings(JsonNode node) {
        List<String> values = new ArrayList<>();
        node.forEach(v -> values.add(v.asText()));
        return values.toArray(String[]::new);
    }
    public static Map<String, Object> run(JsonNode scenario) {
        Map<String, Object> objects = new LinkedHashMap<>();
        List<Object> trace = new ArrayList<>();
        int step = 0;
        for (JsonNode op : scenario.get("operations")) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("step", step++);
            try {
                JsonNode a = op.get("args");
                Object value;
                if (op.get("op").asText().equals("new")) {
                    value = switch (op.get("class").asText()) {
                        case "Option" -> new Option(a.get(0).asText(), a.get(1).asText(), a.get(2).asBoolean(), a.get(3).asText());
                        case "Options" -> new Options();
                        case "DefaultParser" -> new DefaultParser(a.get(0).asBoolean());
                        default -> throw new IllegalArgumentException("Unsupported constructor");
                    };
                } else {
                    Object receiver = objects.get(op.get("on").asText());
                    String method = op.get("method").asText();
                    if (receiver instanceof Option option) {
                        value = switch (method) {
                            case "getOpt" -> option.getOpt();
                            case "getLongOpt" -> option.getLongOpt();
                            case "hasArg" -> option.hasArg();
                            case "isRequired" -> option.isRequired();
                            case "setRequired" -> { option.setRequired(a.get(0).asBoolean()); yield null; }
                            case "getValue" -> option.getValue();
                            case "getValues" -> option.getValues();
                            default -> throw new IllegalArgumentException("Unsupported Option method");
                        };
                    } else if (receiver instanceof Options options) {
                        value = switch (method) {
                            case "addOption" -> options.addOption((Option) objects.get(a.get(0).get("ref").asText()));
                            case "hasOption" -> options.hasOption(a.get(0).asText());
                            case "getRequiredOptions" -> options.getRequiredOptions();
                            default -> throw new IllegalArgumentException("Unsupported Options method");
                        };
                    } else if (receiver instanceof DefaultParser parser) {
                        value = parser.parse((Options) objects.get(a.get(0).get("ref").asText()), strings(a.get(1)), a.get(2).asBoolean());
                    } else if (receiver instanceof CommandLine command) {
                        value = switch (method) {
                            case "hasOption" -> command.hasOption(a.get(0).asText());
                            case "getOptionValue" -> command.getOptionValue(a.get(0).asText());
                            case "getOptionValues" -> command.getOptionValues(a.get(0).asText());
                            case "getArgs" -> command.getArgs();
                            default -> throw new IllegalArgumentException("Unsupported CommandLine method");
                        };
                    } else throw new IllegalArgumentException("Unknown receiver");
                }
                if (op.has("save")) objects.put(op.get("save").asText(), value);
                if (value instanceof Option || value instanceof Options || value instanceof DefaultParser || value instanceof CommandLine) {
                    String canonical = null;
                    for (var entry : objects.entrySet()) if (entry.getValue() == value) { canonical = entry.getKey(); break; }
                    if (canonical == null) throw new IllegalArgumentException("Unbound object result");
                    value = Map.of("ref", canonical);
                }
                if (value instanceof List<?> list) value = new ArrayList<>(list);
                if (value instanceof String[] array) value = array.clone();
                row.put("status", "ok"); row.put("value", value);
            } catch (Exception exception) {
                row.put("status", "exception"); row.put("type", exception.getClass().getSimpleName());
            }
            trace.add(row);
            if (row.get("status").equals("exception")) break;
        }
        return Map.of("id", scenario.get("id").asText(), "status", "ok", "trace", trace);
    }
}

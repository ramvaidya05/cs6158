package lab;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import info.debatty.java.stringsimilarity.*;
import org.graalvm.polyglot.*;
import org.graalvm.polyglot.io.IOAccess;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** JSON batch runner. The reference and guest execute in separate JVM invocations. */
public final class Harness {
    private static final ObjectMapper JSON = new ObjectMapper();

    public static double reference(JsonNode c) {
        String a = c.get("a").isNull() ? null : c.get("a").asText();
        String b = c.get("b").isNull() ? null : c.get("b").asText();
        String op = c.path("operation").asText("distance");
        JsonNode p = c.get("parameter");
        return switch (c.get("task").asText()) {
            case "levenshtein" -> p == null || p.isNull()
                ? new Levenshtein().distance(a, b) : new Levenshtein().distance(a, b, p.asInt());
            case "normalized" -> op.equals("similarity")
                ? new NormalizedLevenshtein().similarity(a, b) : new NormalizedLevenshtein().distance(a, b);
            case "jaro_winkler" -> {
                JaroWinkler j = p == null || p.isNull() ? new JaroWinkler() : new JaroWinkler(p.asDouble());
                yield op.equals("similarity") ? j.similarity(a, b) : j.distance(a, b);
            }
            default -> throw new IllegalArgumentException("Unknown task");
        };
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 1) throw new IllegalArgumentException("reference | graal <candidate.py>");
        JsonNode cases = JSON.readTree(System.in);
        if (!cases.isArray() || cases.isEmpty()) throw new IllegalArgumentException("Nonempty cases array required");
        if (args[0].equals("reference")) {
            List<ObjectNode> rows = new ArrayList<>();
            for (JsonNode c : cases) {
                ObjectNode r = JSON.createObjectNode().put("id", c.get("id").asText());
                try { r.put("status", "ok").put("value", reference(c)); }
                catch (NullPointerException e) { r.put("status", "exception").put("type", "NullPointerException").put("message", e.getMessage()); }
                rows.add(r);
            }
            System.out.println(JSON.writeValueAsString(rows));
        } else if (args[0].equals("graal") && args.length == 2) {
            String candidate = Files.readString(Path.of(args[1]), StandardCharsets.UTF_8);
            // No host lookup, process creation, sockets, or guest filesystem access.
            // OS-level isolation is still required for hostile code and CPU/memory control.
            try (Context ctx = Context.newBuilder("python")
                    .allowHostAccess(HostAccess.NONE).allowHostClassLookup(name -> false)
                    .allowIO(IOAccess.NONE).allowCreateThread(false)
                    .option("engine.WarnInterpreterOnly", "false")
                    .out(System.err).err(System.err).build()) {
                ctx.getBindings("python").putMember("_source", candidate);
                ctx.getBindings("python").putMember("_cases_json", JSON.writeValueAsString(cases));
                Value result = ctx.eval("python", """
                    import json, math, traceback
                    _scope = {'__name__': 'candidate'}
                    try:
                        exec(compile(_source, 'candidate.py', 'exec'), _scope)
                        _fn = _scope['run']
                    except Exception:
                        raise
                    _rows = []
                    for _case in json.loads(_cases_json):
                        _row = {'id': _case['id']}
                        try:
                            _v = _fn(_case['a'], _case['b'], _case['operation'], _case.get('parameter'))
                            if isinstance(_v, bool) or not isinstance(_v, (int, float)) or not math.isfinite(_v):
                                raise TypeError('run must return a finite number, not bool')
                            _row.update(status='ok', value=_v)
                        except Exception as _exc:
                            _row.update(status='exception', type=type(_exc).__name__, message=str(_exc), trace=traceback.format_exc(limit=8))
                        _rows.append(_row)
                    json.dumps(_rows, allow_nan=False)
                    """);
                System.out.println(result.asString());
            }
        } else throw new IllegalArgumentException("Unknown mode");
    }
}

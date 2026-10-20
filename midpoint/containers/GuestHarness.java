package lab;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.graalvm.polyglot.*;
import org.graalvm.polyglot.io.IOAccess;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;

/** Guest-only runner: no Java reference algorithms are present in its image. */
public final class GuestHarness {
    private static final ObjectMapper JSON = new ObjectMapper();
    public static void main(String[] args) throws Exception {
        // Diagnose cache permissions before GraalPy masks them as missing stdlib.
        Path cache = Path.of(System.getProperty("polyglot.engine.userResourceCache"));
        Files.createDirectories(cache);
        Path probe = Files.createTempFile(cache, "write-probe-", ".tmp");
        Files.delete(probe);
        JsonNode cases = JSON.readTree(System.in);
        if (!cases.isArray() || cases.isEmpty()) throw new IllegalArgumentException("Nonempty cases required");
            String candidate = Files.readString(Path.of(args[0]), StandardCharsets.UTF_8);
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
    }
}

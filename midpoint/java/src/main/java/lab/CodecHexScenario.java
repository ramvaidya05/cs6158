package lab;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.apache.commons.codec.DecoderException;
import org.apache.commons.codec.binary.Hex;

/** A deliberately narrow JSON adapter to the pinned Commons Codec Hex API. */
public final class CodecHexScenario {
    private CodecHexScenario() { }

    public static ObjectNode run(JsonNode c) {
        ObjectNode row = JsonNodeFactory.instance.objectNode().put("id", c.path("id").asText());
        try {
            if (c.path("operation").asText().equals("encode")) {
                JsonNode values = c.path("data");
                byte[] bytes = new byte[values.size()];
                for (int i = 0; i < bytes.length; i++) bytes[i] = (byte) values.get(i).asInt();
                row.put("status", "ok").put("value", Hex.encodeHexString(bytes, c.path("lower").asBoolean()));
            } else if (c.path("operation").asText().equals("decode")) {
                byte[] bytes = Hex.decodeHex(c.path("data").asText());
                ArrayNode out = row.put("status", "ok").putArray("value");
                for (byte value : bytes) out.add(Byte.toUnsignedInt(value));
            } else throw new IllegalArgumentException("Unknown Codec operation");
        } catch (DecoderException e) {
            row.put("status", "exception").put("type", "DecoderException");
        }
        return row;
    }
}

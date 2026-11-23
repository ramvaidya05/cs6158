package lab;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.JsonNodeFactory;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.apache.commons.validator.routines.checkdigit.LuhnCheckDigit;
import org.apache.commons.validator.routines.checkdigit.CheckDigitException;

/** Pinned Luhn calculate/isValid contract; null remains null. */
public final class ValidatorScenario {
    private ValidatorScenario() {}
    public static ObjectNode run(JsonNode c) {
        ObjectNode row = JsonNodeFactory.instance.objectNode().put("id", c.path("id").asText());
        String code = c.path("data").isNull() ? null : c.path("data").asText();
        try {
            row.put("status", "ok");
            if (c.path("operation").asText().equals("calculate"))
                row.put("value", LuhnCheckDigit.LUHN_CHECK_DIGIT.calculate(code));
            else if (c.path("operation").asText().equals("isValid"))
                row.put("value", LuhnCheckDigit.LUHN_CHECK_DIGIT.isValid(code));
            else throw new IllegalArgumentException("Unknown Validator operation");
        } catch (CheckDigitException e) {
            row.put("status", "exception").put("type", "CheckDigitException");
        }
        return row;
    }
}

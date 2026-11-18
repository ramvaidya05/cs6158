package lab;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import org.junit.Test;
import static org.junit.Assert.*;

/** Local oracle qualification, not translated-code accuracy or upstream tests. */
public class CsvQualificationTest {
    private final ObjectMapper json = new ObjectMapper();
    private JsonNode run(String input) throws Exception {
        return json.valueToTree(CsvScenario.run(json.readTree(input)));
    }
    @Test public void quotesMultilineAndEmptyFields() throws Exception {
        JsonNode out = run("{\"id\":\"q\",\"operation\":\"parse\",\"text\":\"a,\\\"b,b\\\",\\\"line1\\nline2\\\",\\n\"}");
        assertEquals("ok", out.get("status").asText());
        assertEquals(json.readTree("[[\"a\",\"b,b\",\"line1\\nline2\",\"\"]]"), out.get("value"));
    }
    @Test public void printerExactEscapingAndLineEnding() throws Exception {
        JsonNode out = run("{\"id\":\"p\",\"operation\":\"print\",\"records\":[[\"a,b\",\"say \\\"hi\\\"\",\"\"]]}");
        assertEquals("\"a,b\",\"say \"\"hi\"\"\",\r\n",out.get("value").asText());
    }
    @Test public void malformedQuotedFieldIsParseError() throws Exception {
        assertEquals("CSVParseError",run("{\"id\":\"m\",\"operation\":\"parse\",\"text\":\"\\\"unterminated\"}").get("type").asText());
    }
    @Test public void formatOptionsAndNullMarkers() throws Exception {
        JsonNode out=run("{\"id\":\"c\",\"operation\":\"parse\",\"text\":\" a ;NULL;\\\" b \\\"\\n\",\"config\":{\"delimiter\":\";\",\"trim\":true,\"null_string\":\"NULL\"}}");
        assertEquals(json.readTree("[[\"a\",null,\"b\"]]"),out.get("value"));
    }
    @Test public void invalidOptionTypeRejected() throws Exception {
        assertEquals("IllegalArgumentException",run("{\"id\":\"x\",\"operation\":\"parse\",\"text\":\"\",\"config\":{\"trim\":1}}").get("type").asText());
    }
}

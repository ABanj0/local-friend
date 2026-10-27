"""All split boundaries, prefix leakage, large values and bounded parser state."""
import unittest

from local_agent.redaction import HEADER_LIMIT, StreamRedactor, redact_text


class RedactionTests(unittest.TestCase):
    def stream(self, chunks):
        redactor, output = StreamRedactor(), ""
        for chunk in chunks:
            output += redactor.feed(chunk)
            self.assertLessEqual(redactor.buffered, HEADER_LIMIT)
            self.assertNotIn("CANARY", output)
        output += redactor.finish()
        self.assertEqual(redactor.buffered, 0)
        return output

    def test_all_two_chunk_boundaries_match_final_treatment(self):
        cases = [
            'before password=CANARY after', 'passwd : CANARY; after', 'API_KEY=CANARY,after',
            'quoted prose "password=CANARY" end',
            'apikey = CANARY\nend', 'api-key:\n\t CANARY end', 'token=CANARY', 'secret: CANARY',
            'Authorization: Bearer CANARY.abc-123 end', '{"password": "CANARY space value", "ok": 1}',
            '{"authorization":"Bearer CANARY", "ok":1}',
            '{"token":"CANARY\\\" escaped quote"}', '{"secret": "CANARY\\\\path"}',
            'prefix -----BEGIN RSA PRIVATE KEY-----\nCANARY\n-----END RSA PRIVATE KEY----- suffix',
            '-----BEGIN PRIVATE KEY-----\nCANARY without footer',
            '-----BEGIN CERTIFICATE password=CANARY----- end',
            '-----BEGIN CERTIFICATE -----BEGIN PRIVATE KEY-----\nCANARY\n-----END PRIVATE KEY-----',
        ]
        for text in cases:
            expected = redact_text(text)
            self.assertNotIn("CANARY", expected)
            for boundary in range(len(text) + 1):
                with self.subTest(text=text[:25], boundary=boundary):
                    self.assertEqual(self.stream([text[:boundary], text[boundary:]]), expected)
            self.assertEqual(self.stream(text), expected)

    def test_exact_plain_and_json_output_preserves_surroundings(self):
        self.assertEqual(redact_text('prefix password=CANARY end'), 'prefix password=[REDACTED] end')
        self.assertEqual(redact_text('{"password":"CANARY escaped\\\" data","ok":1}'),
                         '{"password":"[REDACTED]","ok":1}')
        self.assertEqual(redact_text('x -----BEGIN PRIVATE KEY-----\nCANARY\n-----END PRIVATE KEY----- y'),
                         'x [REDACTED PRIVATE KEY] y')

    def test_cancel_at_every_prefix_never_releases_a_value(self):
        for text in ('password=CANARY', 'Bearer CANARY', '{"token":"CANARY"}',
                     '-----BEGIN PRIVATE KEY-----\nCANARY\n-----END PRIVATE KEY-----'):
            for cut in range(len(text) + 1):
                with self.subTest(cut=cut):
                    output = self.stream(text[:cut])
                    # Even partial secret bodies must not be emitted on finish/cancellation.
                    if "CAN" in text[:cut]:
                        self.assertNotIn("CAN", output)

    def test_unbounded_whitespace_and_value_have_bounded_state(self):
        for prefix, suffix in [('password', '=CANARY'), ('password=', 'CANARY'), ('Bearer ', 'CANARY')]:
            redactor, output = StreamRedactor(), ""
            output += redactor.feed(prefix)
            for _ in range(100):
                output += redactor.feed(' \n\t' * 100)
                self.assertLessEqual(redactor.buffered, HEADER_LIMIT)
            output += redactor.feed(suffix) + redactor.finish()
            self.assertNotIn("CANARY", output)
        redactor = StreamRedactor()
        redactor.feed('password=')
        for _ in range(1000):
            self.assertNotIn('CANARY', redactor.feed('CANARY' * 100))
            self.assertLessEqual(redactor.buffered, HEADER_LIMIT)
        self.assertEqual(redactor.finish(), '')

    def test_normal_text_still_streams_and_is_exact(self):
        text = 'Tokenization, secretive wording, passwordless login. Unicode: \u03bb\u4e2d\U0001f600.\n' * 30
        redactor, emitted = StreamRedactor(), []
        for char in text:
            emitted.append(redactor.feed(char))
        self.assertGreater(sum(map(len, emitted)), len(text) - HEADER_LIMIT)
        self.assertEqual(''.join(emitted) + redactor.finish(), text)

    def test_abnormal_private_header_is_conservatively_bounded(self):
        redactor = StreamRedactor()
        output = redactor.feed('-----BEGIN ' + 'A' * 10000 + ' CANARY\n') + redactor.finish()
        self.assertNotIn('CANARY', output)
        self.assertEqual(output, '[REDACTED PRIVATE KEY]')
        self.assertEqual(redactor.buffered, 0)

    def test_redactor_cannot_be_reused_after_finish(self):
        redactor = StreamRedactor()
        redactor.finish()
        with self.assertRaises(ValueError):
            redactor.feed('new response')

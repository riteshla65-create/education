"""Unit checks for retrieval and the AI boundary; no real AI service is called."""
import json
import unittest
from unittest.mock import MagicMock, patch
import tutor


class TutorTests(unittest.TestCase):
    def test_hinglish_and_hindi_aliases(self):
        rows=[{'chapter':8,'page':1,'text':'Matter consists of tiny particles called atoms. Atomic structure includes electrons.'}]
        for question in ['parmanu kya hai?', 'परमाणु क्या है?', 'atoms kya hote hain?']:
            self.assertEqual(tutor.rank_passages(rows,question)[0]['chapter'],8)
        self.assertEqual(tutor.rank_passages(rows,'photosynthesis'),[])

    def test_distinct_keywords_beat_repetition(self):
        rows=[{'chapter':1,'page':1,'text':'velocity '*20},{'chapter':4,'page':2,'text':'Velocity and acceleration describe changing motion.'}]
        result=tutor.rank_passages(rows,'velocity acceleration')
        self.assertEqual(result[0]['page'],2)

    def test_ai_request_uses_sources_and_does_not_store(self):
        sources=[{'chapter':8,'page':1,'text':'Matter consists of atoms.'}]
        response=MagicMock()
        response.__enter__.return_value.read.return_value=json.dumps({'output':[{'type':'message','content':[{'type':'output_text','text':'An atom is a tiny building block of matter.'}]}]}).encode()
        with patch.dict('os.environ',{'OPENAI_API_KEY':'synthetic-test-key','OPENAI_MODEL':'synthetic-test-model'},clear=True),patch('tutor.urlopen',return_value=response) as request:
            answer=tutor.explain_with_ai('Atom kya hota hai?','Exploration',sources,'Hinglish')
        self.assertIn('building block',answer)
        call=request.call_args[0][0]
        payload=json.loads(call.data)
        self.assertEqual(call.full_url,'https://api.openai.com/v1/responses')
        self.assertFalse(payload['store'])
        self.assertEqual(payload['model'],'synthetic-test-model')
        self.assertIn('Hinglish',payload['instructions'])
        self.assertIn('General explanation',payload['instructions'])
        self.assertEqual(json.loads(payload['input'][0]['content'].split(': ',1)[1])['sources'],sources)
        self.assertNotIn('synthetic-test-key',json.dumps(payload['input']))

    def test_ai_needs_config_and_strict_mode_needs_sources(self):
        with patch.dict('os.environ',{},clear=True),patch('tutor.urlopen') as request:
            self.assertIsNone(tutor.explain_with_ai('atom','Science',[{'chapter':1,'page':1,'text':'atom'}],'English'))
            request.assert_not_called()
        with patch.dict('os.environ',{'OPENAI_API_KEY':'synthetic','OPENAI_MODEL':'synthetic'},clear=True),patch('tutor.urlopen') as request:
            self.assertIsNone(tutor.explain_with_ai('atom','Science',[],'English',scope='book'))
            request.assert_not_called()

    def test_general_question_without_matches_keeps_conversation(self):
        response=MagicMock()
        response.__enter__.return_value.read.return_value=json.dumps({'output':[{'type':'message','content':[{'type':'output_text','text':'General explanation: x = 6.'}]}]}).encode()
        history=[{'role':'user','content':'Solve 2x + 7 = 19'},{'role':'assistant','content':'x = 6'}]
        with patch.dict('os.environ',{'OPENAI_API_KEY':'synthetic','OPENAI_MODEL':'synthetic'},clear=True),patch('tutor.urlopen',return_value=response) as request:
            answer=tutor.explain_with_ai('Isko simple samjhao','Maths',[],'Hinglish',history)
        self.assertIn('x = 6',answer)
        payload=json.loads(request.call_args[0][0].data)
        self.assertEqual(payload['input'][1:3],history)
        self.assertEqual(payload['input'][-1],{'role':'user','content':'Isko simple samjhao'})
        self.assertEqual(json.loads(payload['input'][0]['content'].split(': ',1)[1])['sources'],[])
        self.assertFalse(payload['store'])

    def test_book_scope_and_incomplete_answer(self):
        response=MagicMock();response.__enter__.return_value.read.return_value=b'{"status":"incomplete","output":[{"type":"message","content":[{"type":"output_text","text":"Partial steps"}]}]}'
        with patch.dict('os.environ',{'OPENAI_API_KEY':'synthetic','OPENAI_MODEL':'synthetic'},clear=True),patch('tutor.urlopen',return_value=response) as request:
            with self.assertRaises(ValueError):
                tutor.explain_with_ai('atom','Science',[{'chapter':1,'page':1,'text':'atom'}],'English',scope='book')
        self.assertIn('Use only',json.loads(request.call_args[0][0].data)['instructions'])

    def test_ai_rejects_empty_output(self):
        response=MagicMock();response.__enter__.return_value.read.return_value=b'{"output":[]}'
        with patch.dict('os.environ',{'OPENAI_API_KEY':'synthetic','OPENAI_MODEL':'synthetic'},clear=True),patch('tutor.urlopen',return_value=response):
            with self.assertRaises(ValueError):
                tutor.explain_with_ai('atom','Science',[{'chapter':1,'page':1,'text':'atom'}],'English')


if __name__=='__main__':unittest.main()

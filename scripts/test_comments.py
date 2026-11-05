"""Persistence and anonymous comment semantics, with real temporary SQLite databases."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('comments',ROOT/'api/comments.py')
api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)


class CommentsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.file=Path(self.tmp.name)/'comments.sqlite3'
        self.db=api.Database(sqlite_path=self.file)
        with self.db.connect() as c:
            self.a,self.token=self.db.visitor(c,None)
            self.b,_=self.db.visitor(c,None)

    def tearDown(self):
        self.tmp.cleanup()

    def payload(self, **kw):
        return {'body':'Nice arc.', 'name':'', 'request_id':'12345678-1234-1234-1234-123456789012',**kw}

    def test_shared_persistence_and_anonymous_cookie(self):
        with self.db.connect() as c:
            self.db.post(c,'video-one',self.a,self.payload())
        reopened=api.Database(sqlite_path=self.file)
        with reopened.connect() as c:
            rows=reopened.comments(c,'video-one',self.b)['comments']
            self.assertEqual(rows[0]['body'],'Nice arc.')
            self.assertTrue(rows[0]['name'].startswith('Guest '))
            self.assertEqual(reopened.visitor(c,self.token),(self.a,None))

    def test_retry_is_idempotent(self):
        with self.db.connect() as c:
            a=self.db.post(c,'one',self.a,self.payload())
            b=self.db.post(c,'one',self.a,self.payload())
            self.assertEqual(a,b);self.assertEqual(self.db.count(c,'one'),1)
            with self.assertRaises(api.BadRequest):
                self.db.post(c,'one',self.a,self.payload(body='different'))

    def test_reply_and_video_isolation(self):
        with self.db.connect() as c:
            parent=self.db.post(c,'one',self.a,self.payload())
            self.db.post(c,'one',self.b,self.payload(parent_id=parent))
            roots=self.db.comments(c,'one',self.a)['comments']
            self.assertEqual(len(roots),1);self.assertEqual(roots[0]['reply_count'],1)
            self.assertEqual(self.db.count(c,'one'),2)
            self.assertEqual(len(self.db.comments(c,'one',self.a,parent=parent)['comments']),1)
            self.assertEqual(self.db.comments(c,'two',self.a)['comments'],[])
            with self.assertRaises(api.BadRequest):
                self.db.post(c,'two',self.b,self.payload(parent_id=parent,request_id='a'*32))

    def test_like_dislike_and_cancel_one_vote_per_visitor(self):
        with self.db.connect() as c:
            cid=self.db.post(c,'one',self.a,self.payload())
            def vote(value):return self.db.vote(c,'one',self.b,{'comment_id':cid,'value':value})
            self.assertEqual(vote(1)['likes'],1);self.assertEqual(vote(1)['likes'],1)
            self.assertEqual(vote(-1),{'likes':0,'my_vote':-1})
            self.assertEqual(vote(0),{'likes':0,'my_vote':0})

    def test_top_newest_and_pagination(self):
        with self.db.connect() as c:
            first=None
            for i in range(23):
                cid=self.db.post(c,'one',self.a,self.payload(body=str(i),request_id=f'{i:032x}'))
                self.db.query(c,'UPDATE hc_comments SET created_at=? WHERE id=?',(i,cid))
                if i==0:first=cid
            self.db.vote(c,'one',self.b,{'comment_id':first,'value':1})
            top=self.db.comments(c,'one',self.a)
            self.assertEqual(top['comments'][0]['id'],first);self.assertEqual(top['next_offset'],20)
            newest=self.db.comments(c,'one',self.a,sort='newest')
            self.assertEqual(newest['comments'][0]['body'],'22')
            self.assertEqual(len(self.db.comments(c,'one',self.a,offset=20)['comments']),3)

    def test_content_is_not_moderated_and_sql_is_parameterized(self):
        body='<script>alert(1)</script> https://example.com/ — I disagree. 这是评论'
        with self.db.connect() as c:
            self.db.post(c,'one',self.a,self.payload(body=body,name="' OR 1=1 --"))
            row=self.db.comments(c,'one',self.b)['comments'][0]
            self.assertEqual(row['body'],body);self.assertEqual(row['is_example'],0)

    def test_invalid_inputs_rejected_without_review_queue(self):
        for payload in [self.payload(body=' '),self.payload(body='x'*3001),self.payload(name='x'*41),self.payload(request_id='bad')]:
            with self.db.connect() as c:
                with self.assertRaises(api.BadRequest):self.db.post(c,'one',self.a,payload)

    def test_vercel_never_uses_temporary_sqlite_as_production(self):
        with patch.dict('os.environ',{'VERCEL':'1'}):
            with self.assertRaises(RuntimeError):api.Database(sqlite_path=self.file)


if __name__=='__main__':unittest.main(verbosity=2)

import {database,closeDatabase,commentsSchema} from '../lib/comments.js';
import {readFileSync} from 'node:fs';
const sql=readFileSync(new URL('../lib/comments-schema.sql',import.meta.url),'utf8').replace(/\bhc_comment(?:s|_rates|_reports|_actions|_votes)\b/g,name=>commentsSchema+'.'+name);
await database().query(sql);
await closeDatabase();console.log('Comments schema ready.');

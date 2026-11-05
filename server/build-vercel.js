// Public assets only. Server source, tests, credentials and SQL never enter the static output.
import {readdir,cp,mkdir,rm} from 'node:fs/promises';
const root=new URL('../',import.meta.url);const out=new URL('../dist/',import.meta.url);await rm(out,{recursive:true,force:true});await mkdir(out,{recursive:true});
const directories=new Set(['assets','blog','demo','templates','tools','videos']);
for(const entry of await readdir(root,{withFileTypes:true})){
 if((entry.isDirectory()&&directories.has(entry.name))||(entry.isFile()&&/\.(html|xml|txt|ico|svg|png|webmanifest)$/.test(entry.name)))await cp(new URL(entry.name,root),new URL(entry.name,out),{recursive:true});
}
console.log('Static output ready; /api/comments is bundled separately by Vercel.');

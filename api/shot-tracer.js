import {proxy} from '../lib/shot-tracer-bridge.js';
export default (req,res)=>proxy(req,res,false);

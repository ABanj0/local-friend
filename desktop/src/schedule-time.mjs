/** UTC elapsed intervals are independent of these explicit display-zone offsets. */
export function scheduleTime(milliseconds,timeZone){
  if(!Number.isSafeInteger(milliseconds)||milliseconds<0||!Number.isFinite(new Date(milliseconds).getTime()))return 'Invalid saved slot; review this schedule';
  try{return new Intl.DateTimeFormat('en-CA',{timeZone,dateStyle:'medium',timeStyle:'long'}).format(new Date(milliseconds));}
  catch{return new Date(milliseconds).toISOString()+' (UTC; display timezone unavailable)';}
}

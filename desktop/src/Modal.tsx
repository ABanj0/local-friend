import {useLayoutEffect,useRef,type ReactNode} from 'react';

/** Native modal semantics keep background controls inert, including with stacked dialogs. */
export function Modal({title,children,onDismiss,className=''}:{
  title:string;children:ReactNode;onDismiss:()=>void;className?:string;
}) {
  const ref=useRef<HTMLDialogElement>(null);
  useLayoutEffect(()=>{
    const dialog=ref.current!;
    const opener=document.activeElement instanceof HTMLElement?document.activeElement:null;
    dialog.showModal();
    dialog.querySelector<HTMLElement>('[data-dialog-initial]')?.focus();
    return ()=>{
      dialog.close();
      // close() normally restores focus. Cover a removed/disabled initial control without
      // stealing focus from a newer modal or from an intentional navigation target.
      if(document.activeElement===document.body&&opener?.isConnected)opener.focus();
    };
  },[]);
  return <dialog ref={ref} className={`approval-modal ${className}`} aria-labelledby={title}
    onKeyDown={event=>{
      if(event.key!=='Tab')return;
      const controls=Array.from(ref.current!.querySelectorAll<HTMLElement>(
        'button,input,select,textarea,a[href],summary,[tabindex]'))
        .filter(control=>control.tabIndex>=0&&!control.matches(':disabled')&&control.getClientRects().length>0);
      const first=controls[0],last=controls.at(-1);
      if(!first){event.preventDefault();return;}
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
    }}
    onCancel={event=>{event.preventDefault();onDismiss();}}>{children}</dialog>;
}

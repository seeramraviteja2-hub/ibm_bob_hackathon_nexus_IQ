import { InputHTMLAttributes, LabelHTMLAttributes, forwardRef } from "react";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className = "", ...props }, ref) => (
    <input ref={ref}
      className={`w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm placeholder-white/30 focus:outline-none focus:border-indigo-500 transition ${className}`}
      {...props} />
  )
);
Input.displayName = "Input";

export function Label({ className = "", ...props }: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label className={`text-xs text-white/50 uppercase tracking-widest ${className}`} {...props} />
  );
}

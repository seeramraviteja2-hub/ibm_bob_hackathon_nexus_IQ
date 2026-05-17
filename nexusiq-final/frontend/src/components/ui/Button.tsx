import { ButtonHTMLAttributes, forwardRef } from "react";
import { Loader2 } from "lucide-react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = "", variant = "primary", size = "md", isLoading, disabled, children, ...props }, ref) => {
    const base = "inline-flex items-center justify-center gap-2 font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed";
    const variants = {
      primary:   "bg-indigo-600 hover:bg-indigo-500 text-white",
      secondary: "bg-white/10 hover:bg-white/15 text-white",
      ghost:     "text-white/60 hover:text-white hover:bg-white/5",
    };
    const sizes = {
      sm: "text-xs px-3 py-1.5",
      md: "text-sm px-4 py-2.5",
      lg: "text-base px-6 py-3",
    };
    return (
      <button ref={ref} className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
        disabled={isLoading || disabled} {...props}>
        {isLoading && <Loader2 size={14} className="animate-spin" />}
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

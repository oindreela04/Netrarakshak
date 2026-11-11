import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-semibold transition-colors disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-navy text-white hover:bg-navy-700",
        primary: "bg-clinical text-white hover:bg-clinical-600",
        teal: "bg-teal text-white hover:bg-teal-600",
        outline: "border border-line bg-white text-ink hover:bg-mist",
        ghost: "text-ink hover:bg-mist",
        danger: "bg-danger text-white hover:bg-danger/90",
        link: "text-clinical underline-offset-4 hover:underline px-0",
        inverse: "bg-white text-navy hover:bg-white/90",
      },
      size: { default: "h-10 px-4", sm: "h-8 px-3 text-[13px]", lg: "h-12 px-6 text-[15px]", icon: "h-9 w-9" },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild, ...props }, ref) => {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant, size }), className)} ref={ref} {...props} />;
});
Button.displayName = "Button";
export { buttonVariants };

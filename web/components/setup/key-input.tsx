"use client";

import * as React from "react";
import { Eye, EyeOff } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface Props {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function KeyInput({ value, onChange, placeholder, disabled }: Props) {
  const [show, setShow] = React.useState(false);
  return (
    <div className="relative">
      <Input
        type={show ? "text" : "password"}
        autoComplete="off"
        spellCheck={false}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder ?? "sk-..."}
        className="pr-10"
        disabled={disabled}
      />
      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={() => setShow((s) => !s)}
        className="absolute end-1 top-1 h-8 w-8"
        aria-label={show ? "Hide key" : "Show key"}
      >
        {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </Button>
    </div>
  );
}

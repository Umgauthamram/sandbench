"use client";

/**
 * MarkdownRenderer – renders AI-generated analysis text as formatted HTML.
 * Uses react-markdown + remark-gfm for full GitHub-flavored markdown support.
 */
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  return (
    <div className={`prose-analysis ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Headings
          h1: ({ children }) => (
            <h1 className="mb-3 mt-5 text-base font-bold text-zinc-100 first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="mb-2 mt-4 text-sm font-semibold text-zinc-200 first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mb-2 mt-3 text-sm font-semibold text-zinc-300 first:mt-0">
              {children}
            </h3>
          ),

          // Paragraphs — preserve blank lines between sections
          p: ({ children }) => (
            <p className="mb-3 text-sm leading-relaxed text-zinc-400 last:mb-0">
              {children}
            </p>
          ),

          // Strong / bold
          strong: ({ children }) => (
            <strong className="font-semibold text-zinc-200">{children}</strong>
          ),

          // Emphasis / italic
          em: ({ children }) => (
            <em className="italic text-zinc-300">{children}</em>
          ),

          // Ordered list
          ol: ({ children }) => (
            <ol className="mb-3 ml-4 list-decimal space-y-1.5 last:mb-0">
              {children}
            </ol>
          ),

          // Unordered list
          ul: ({ children }) => (
            <ul className="mb-3 ml-4 list-disc space-y-1.5 last:mb-0">
              {children}
            </ul>
          ),

          // List item
          li: ({ children }) => (
            <li className="text-sm leading-relaxed text-zinc-400">{children}</li>
          ),

          // Inline code
          code: ({ children, className: cls }) => {
            const isBlock = cls?.startsWith("language-");
            if (isBlock) {
              return (
                <code className="block overflow-auto rounded-lg bg-zinc-950 px-4 py-3 font-mono text-xs leading-6 text-zinc-300 ring-1 ring-zinc-800">
                  {children}
                </code>
              );
            }
            return (
              <code className="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-xs text-amber-300 ring-1 ring-zinc-700">
                {children}
              </code>
            );
          },

          // Fenced code blocks
          pre: ({ children }) => (
            <pre className="mb-3 overflow-auto rounded-lg bg-zinc-950 p-4 font-mono text-xs leading-6 ring-1 ring-zinc-800 last:mb-0">
              {children}
            </pre>
          ),

          // Horizontal rule
          hr: () => <hr className="my-4 border-zinc-800" />,

          // Blockquote
          blockquote: ({ children }) => (
            <blockquote className="mb-3 border-l-2 border-zinc-700 pl-4 text-sm italic text-zinc-500 last:mb-0">
              {children}
            </blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

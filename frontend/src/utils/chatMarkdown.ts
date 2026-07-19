import DOMPurify from "dompurify";
import { marked } from "marked";

marked.setOptions({
  breaks: true,
  gfm: true,
});

export function renderChatMarkdown(text: string): string {
  const source = text || "";
  const raw = marked.parse(source, { async: false }) as string;
  return DOMPurify.sanitize(raw, {
    USE_PROFILES: { html: true },
  });
}

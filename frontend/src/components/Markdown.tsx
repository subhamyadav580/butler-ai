import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export function Markdown({ text }: { text: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: (props) => <a {...props} target="_blank" rel="noreferrer" />,
          // Thumbnail size comes from CSS; click opens the full image
          img: ({ src, alt }) => (
            <a href={typeof src === 'string' ? src : undefined} target="_blank" rel="noreferrer">
              <img src={src} alt={alt ?? ''} loading="lazy" />
            </a>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  )
}

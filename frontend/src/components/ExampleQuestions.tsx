interface Props {
  onQuestionClick: (question: string) => void
}

const examples = [
  {
    icon: '📊',
    question: 'Show me total revenue by agent',
  },
  {
    icon: '💰',
    question: 'What is the total revenue for last quarter?',
  },
  {
    icon: '🏢',
    question: 'Show me top performing companies',
  },
  {
    icon: '📈',
    question: 'Show revenue trends by month',
  },
  {
    icon: '👥',
    question: 'List all agents with their total sales',
  },
  {
    icon: '🎯',
    question: 'What are the highest value transactions?',
  },
]

export default function ExampleQuestions({ onQuestionClick }: Props) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-4xl mx-auto">
      {examples.map((example, idx) => (
        <button
          key={idx}
          onClick={() => onQuestionClick(example.question)}
          className="flex items-start space-x-3 p-4 bg-white border border-gray-200 rounded-xl hover:border-blue-500 hover:shadow-md transition text-left group"
        >
          <span className="text-2xl">{example.icon}</span>
          <span className="text-sm text-gray-700 group-hover:text-blue-600 transition">
            {example.question}
          </span>
        </button>
      ))}
    </div>
  )
}

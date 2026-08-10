export default function Strengths({ strengths }) {
  return (
    <section className="panel">
      <h3 className="panel-title">💪 Strengths</h3>
      {strengths.length === 0 ? (
        <p className="empty-note">Keep improving your resume to unlock strengths!</p>
      ) : (
        <ul className="bullet-list good">
          {strengths.map((item, i) => <li key={i}>{item}</li>)}
        </ul>
      )}
    </section>
  )
}

export function EvidenceLinks({ ids }: { ids: string[] }) {
  const visit = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => document.getElementById(id)?.focus(), 450);
  };

  return (
    <div className="evidence" aria-label="Transcript evidence">
      <span>Evidence</span>
      {ids.map((id) => (
        <button key={id} type="button" onClick={() => visit(id)}>
          {id}
        </button>
      ))}
    </div>
  );
}

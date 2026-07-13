import { useState } from "react";
import type { StudyPack } from "../types";
import { EvidenceLinks } from "./EvidenceLinks";

type Tab = "notes" | "concepts" | "flashcards" | "quiz";

export function StudyPackView({ pack }: { pack: StudyPack }) {
  const [tab, setTab] = useState<Tab>("notes");
  const [answers, setAnswers] = useState<Record<number, number>>({});

  return (
    <section className="study-pack" aria-labelledby="study-pack-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Study pack</p>
          <h2 id="study-pack-heading">{pack.title}</h2>
        </div>
      </div>
      <p className="overview">{pack.overview}</p>
      <div className="tabs" role="tablist" aria-label="Study pack sections">
        {(["notes", "concepts", "flashcards", "quiz"] as Tab[]).map((item) => (
          <button
            type="button"
            role="tab"
            aria-selected={tab === item}
            className={tab === item ? "active" : ""}
            onClick={() => setTab(item)}
            key={item}
          >
            {item}
          </button>
        ))}
      </div>

      <div className="cards" role="tabpanel">
        {tab === "notes" &&
          pack.notes.map((note) => (
            <article className="content-card" key={`${note.title}-${note.segment_ids[0]}`}>
              <h3>{note.title}</h3>
              <p>{note.body}</p>
              <EvidenceLinks ids={note.segment_ids} />
            </article>
          ))}
        {tab === "concepts" &&
          pack.concepts.map((concept) => (
            <article className="content-card" key={`${concept.name}-${concept.segment_ids[0]}`}>
              <h3>{concept.name}</h3>
              <p>{concept.definition}</p>
              <EvidenceLinks ids={concept.segment_ids} />
            </article>
          ))}
        {tab === "flashcards" &&
          pack.flashcards.map((card, index) => (
            <article className="content-card flashcard" key={`${card.front}-${index}`}>
              <p className="card-label">Front</p>
              <h3>{card.front}</h3>
              <div className="divider" />
              <p className="card-label">Back</p>
              <p>{card.back}</p>
              <EvidenceLinks ids={card.segment_ids} />
            </article>
          ))}
        {tab === "quiz" &&
          pack.quiz.map((question, questionIndex) => {
            const selected = answers[questionIndex];
            return (
              <article className="content-card quiz" key={`${question.question}-${questionIndex}`}>
                <h3>{questionIndex + 1}. {question.question}</h3>
                <div className="options">
                  {question.options.map((option, optionIndex) => {
                    const revealed = selected !== undefined;
                    const correct = optionIndex === question.correct_answer;
                    const selectedWrong = selected === optionIndex && !correct;
                    return (
                      <button
                        type="button"
                        className={`${revealed && correct ? "correct" : ""} ${selectedWrong ? "wrong" : ""}`}
                        onClick={() => setAnswers((current) => ({ ...current, [questionIndex]: optionIndex }))}
                        key={option}
                      >
                        {option}
                      </button>
                    );
                  })}
                </div>
                {selected !== undefined && <p className="explanation">{question.explanation}</p>}
                <EvidenceLinks ids={question.segment_ids} />
              </article>
            );
          })}
      </div>
    </section>
  );
}

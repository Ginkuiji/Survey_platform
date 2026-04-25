import { create } from "zustand";

export const useEditorStore = create(set => ({
  questions: [],
  addQuestion: q =>
    set(state => ({ questions: [...state.questions, q] })),
  removeQuestion: id =>
    set(state => ({ questions: state.questions.filter(q => q.id !== id) }))
}));

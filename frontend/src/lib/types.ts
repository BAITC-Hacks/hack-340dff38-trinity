export type Role = "STUDENT" | "COMPANY" | "ADMIN";
export interface User {
  id: number;
  name: string;
  role: Role;
  email: string;
  companyId: number | null;
}
export interface Company {
  id: number;
  name: string;
  description: string;
  industry: string;
  city: string;
  email: string;
  telegram: string;
}
export interface Criterion {
  score: number;
  maxScore: number;
  reasoning: string;
  missing: string[];
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
}
export interface Analysis {
  overallScore: number;
  source: string;
  criteria: Record<string, Criterion>;
}
export interface SolutionAnalysis extends Analysis {
  summary: string;
  keyStrengths: string[];
  keyRisks: string[];
  recommendedImprovements: string[];
}
export interface Member {
  id: number;
  fullName: string;
  university: string;
  email?: string;
  githubUrl?: string;
  portfolioUrl?: string;
}
export interface Team {
  id: number;
  name: string;
  members: Member[];
  locked: boolean;
}
export interface Submission {
  id: string;
  label: string;
  anonymousNumber: number;
  title: string;
  summary: string;
  solutionDescription: string;
  implementationDetails: string;
  status: string;
  anonymous: boolean;
  aiAnalysis: SolutionAnalysis | null;
  teamId?: number;
  teamName?: string;
  members?: Member[];
  demoUrl?: string;
  repositoryUrl?: string;
  projectFileName?: string;
  problemId?: number;
  problemTitle?: string;
  deadline?: string;
}
export interface PublicText {
  id: number;
  text: string;
  author: string;
  createdAt: string;
}
export interface Question extends PublicText {
  answers: PublicText[];
}
export interface Problem {
  id: number;
  title: string;
  company: Company;
  industry: string;
  context: string;
  need: string;
  users: string;
  availableData: string;
  constraints: string;
  expectedResult: string;
  successCriteria: string;
  businessContact: string;
  interactionFormat: string;
  qualityScore: number;
  readiness: string;
  qualityAnalysis: Analysis;
  deadline: string;
  status: string;
  submissionCount: number;
  acceptingSubmissions: boolean;
  winnerSubmissionId: string | null;
  companyScore: number | null;
  feedback: string | null;
  completed: boolean;
  hidden: boolean;
  updatedAt: string;
  questions: Question[];
  comments: PublicText[];
  revisions: { id: number; changedFields: string[]; createdAt: string }[];
  winner: Submission | null;
}
export type Card = Pick<
  Problem,
  | "title"
  | "context"
  | "need"
  | "users"
  | "availableData"
  | "constraints"
  | "expectedResult"
  | "successCriteria"
  | "businessContact"
  | "interactionFormat"
  | "industry"
>;
export interface Profile {
  id: number;
  fullName: string;
  email: string;
  university: string;
  specialization: string;
  course: number;
  skills: string[];
  interests: string[];
  githubUrl: string;
  portfolioUrl: string;
  totalPoints: string;
}
export interface Points {
  totalPoints: string;
  transactions: {
    id: number;
    problemId: number;
    problemTitle: string;
    points: string;
    createdAt: string;
    reason: string;
  }[];
}
export interface Interview {
  questions: { id: string; question: string }[];
  draft: Card;
  missingFields: string[];
  source: string;
}
export interface Advice {
  days: number;
  reason: string;
  source: string;
}
export interface Message {
  id: number;
  text: string;
  sender: string;
  isMine: boolean;
  createdAt: string;
}

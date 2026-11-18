import { atom } from 'nanostores'

/** Where first-run onboarding is: `shown` while it runs, then how it ended. */
export type OnboardingPhase = 'done' | 'failed' | 'idle' | 'shown' | 'skipped'

export const $onboardingPhase = atom<OnboardingPhase>('idle')

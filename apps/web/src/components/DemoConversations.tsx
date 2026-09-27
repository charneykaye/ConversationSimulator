// SPDX-License-Identifier: Apache-2.0
//
// The demo edition's five-conversation picker (issue #495). Replaces the full
// Scenario Library on the demo Home screen: no search, no filters, no folders —
// five cards, each one click from a real conversation.
//
// The five come from the engine (GET /api/health → demo.scenario_ids), rendered
// in the engine's curated order. When the engine has not reported a demo list
// (older core, or a bundle built as demo against a full engine in dev) the
// cards fall back to whatever the scenario list returns, so the screen never
// dead-ends.
import { Link } from 'react-router-dom'
import type { ScenarioInfo } from '@convsim/shared'
import { useScenarios } from '../api/useScenarios'
import { useEdition } from '../edition'
import { useTranslation } from '../i18n'

// The scripted tutorial is internal content (issue #473) and never a card.
const _HIDDEN_SCENARIO_IDS = new Set(['first_words_tutorial'])

export function orderDemoScenarios(
  scenarios: ScenarioInfo[],
  curatedIds: string[] | null,
): ScenarioInfo[] {
  const visible = scenarios.filter((s) => !_HIDDEN_SCENARIO_IDS.has(s.scenario_id))
  if (!curatedIds || curatedIds.length === 0) return visible
  const byId = new Map(visible.map((s) => [s.scenario_id, s]))
  return curatedIds.map((id) => byId.get(id)).filter((s): s is ScenarioInfo => s != null)
}

export default function DemoConversations() {
  const { t } = useTranslation()
  const { demo } = useEdition()
  const result = useScenarios()

  const cards = orderDemoScenarios(result.scenarios, demo?.scenario_ids ?? null)

  return (
    <section aria-label={t('demo.conversations.heading')} data-testid="demo-conversations">
      <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.25rem' }}>
        {t('demo.conversations.heading')}
      </h2>
      <p style={{ margin: '0 0 0.85rem', color: '#a1a1aa', fontSize: '0.875rem' }}>
        {t('demo.conversations.subheading')}
      </p>

      {result.state === 'loading' && (
        <p style={{ color: '#71717a', fontSize: '0.875rem' }} aria-busy="true">
          {t('demo.conversations.loading')}
        </p>
      )}
      {result.state === 'error' && (
        <p role="alert" style={{ color: '#f87171', fontSize: '0.875rem' }}>
          {t('demo.conversations.error')}
        </p>
      )}
      {result.state === 'ready' && cards.length === 0 && (
        <p role="status" style={{ color: '#fbbf24', fontSize: '0.875rem' }}>
          {t('demo.conversations.empty')}
        </p>
      )}

      {cards.length > 0 && (
        <ol
          style={{
            listStyle: 'none',
            padding: 0,
            margin: 0,
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(17rem, 1fr))',
            gap: '0.75rem',
          }}
        >
          {cards.map((s, i) => (
            <li
              key={s.scenario_id}
              data-testid="demo-conversation-card"
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.4rem',
                padding: '1rem 1.1rem',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '10px',
                background: 'rgba(255,255,255,0.03)',
              }}
            >
              <p
                style={{
                  margin: 0,
                  fontSize: '0.75rem',
                  color: '#a5b4fc',
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  fontWeight: 600,
                }}
              >
                {t('demo.conversations.ordinal', { n: i + 1 })} · {s.pack_name}
              </p>
              <h3 style={{ margin: 0, fontSize: '1.05rem', color: '#f4f4f5' }}>{s.title}</h3>
              <p style={{ margin: 0, fontSize: '0.825rem', color: '#a1a1aa', lineHeight: 1.5 }}>
                {s.summary}
              </p>
              <p style={{ margin: '0.15rem 0 0', fontSize: '0.8rem', color: '#71717a' }}>
                {t('demo.conversations.role', { role: s.player_role.label })} ·{' '}
                {s.estimated_length_label}
                {s.supported_languages.length > 0 && !s.supported_languages.includes('en')
                  ? ` · ${t('demo.conversations.language', { code: s.supported_languages[0] })}`
                  : ''}
              </p>
              <Link
                to={`/setup/${s.scenario_id}`}
                aria-label={t('demo.conversations.startLabel', { title: s.title })}
                style={{
                  marginTop: 'auto',
                  alignSelf: 'flex-start',
                  padding: '0.4rem 0.9rem',
                  borderRadius: '4px',
                  background: 'rgba(99,102,241,0.85)',
                  color: '#fff',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  textDecoration: 'none',
                }}
              >
                {t('demo.conversations.start')}
              </Link>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

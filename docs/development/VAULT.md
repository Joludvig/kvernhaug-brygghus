# Kvernhaug Brygghus — Obsidian Vault

*Del av KBDP. Se [../../CLAUDE.md](../../CLAUDE.md) for oversikt over hele dokumentsystemet.*

## Hva Vault-en er

En separat, frittstående Obsidian-vault ved `C:\Vault\Kvernhaug Brygghus` — **ikke** en del av dette app-repoet, og ikke git-sporet sammen med det. Den inneholder en "Canon Foundation": kanoniske notater om ølidentiteter, kildehistorikk og prosjektstatus, bygget med en status/source_layer-metadatamodell (FACT/PROBABLE-merking av kildemateriale under `Canon/Kilder/`) og et "Handover"-dokument som bevisst bygger bro mellom Vault-en og den faktiske kodetilstanden i dette repoet.

Se også [[kvernhaug_method]] (i minnesystemet) for Kvernhaug-metoden — designfilosofien (Følelse → Identitet → Sanseprofil → Oppskrift → Brygging → Iterasjon) som er det høyeste designprinsippet for ølrelaterte beslutninger, og som Canon-notatene i Vault-en er bygget rundt.

## Regel

Undersøk automatisk (fase 4 i [WORKFLOW.md](WORKFLOW.md)) om Vault-en bør oppdateres når arbeidet gjelder:

- nye funksjoner som endrer brukeropplevelsen på en måte Canon-notatene beskriver
- arkitekturendringer som Handover-dokumentet refererer til
- nye workflows eller moduler av betydning for ølidentitetene (Sommerglød, Skumring, Eldsvenn, Ragnarok m.fl.)
- API-/dataendringer som Kilder-notatene bygger på

Oppdater **kun** de konkrete Vault-filene som faktisk er relevante — ikke gjør en generell gjennomgang av hele Vault-en for en liten kodeendring. Rapporter i sluttrapporten hvilke Vault-filer som ble endret (eller bekreft eksplisitt at ingen var relevante, og hvorfor).

## Kjente begrensninger ved dette dokumentet

Dette er et bevisst kort oppslagsdokument, ikke en fullstendig Canon-taksonomi. Full Canon-notatstruktur (hvilke undermapper, hvilken navnekonvensjon på Kilder-notater, hvordan status/source_layer-feltene brukes i praksis) er ikke gjentatt her for å unngå at to kilder til sannhet driver fra hverandre — Vault-en selv er autoritativ for sin egen struktur. Hvis en fremtidig økt trenger å gjøre en større, strukturert gjennomgang av Vault-en, bør det gjøres som en egen, avgrenset oppgave med direkte lesetilgang til `C:\Vault\Kvernhaug Brygghus`, ikke utledes fra dette dokumentet alene.

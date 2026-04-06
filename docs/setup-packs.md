# Setup Packs for Hermes WebUI

This document describes one-click setup pack concepts surfaced inside the WebUI so general users can bootstrap common workflows quickly.

## 1. Obsidian Starter Pack

Goal:
Install and configure the core Obsidian workflow helpers needed for note-centric Hermes usage.

Typical scope:
- verify Obsidian vault path
- install or verify Obsidian CLI availability
- prepare Obsidian-friendly markdown workflow
- verify note creation / search / save flow

## 2. ShareNote + Telegram Publishing Pack

Goal:
Set up the common "note -> ShareNote link -> deliver back to Telegram" workflow.

Typical scope:
- verify ShareNote plugin availability
- verify Obsidian Advanced URI support
- verify local automation helper script
- create or validate share-link generation flow
- ensure final response includes saved path + share URL

## 3. Obsidian Power Workflow Pack

Goal:
Combine note creation, posting, ShareNote, and Telegram handoff into a reusable publishing workflow.

Typical scope:
- note templates
- posting workflow defaults
- share-link generation
- Telegram-friendly result handoff
- optional memory / skill setup

## UI expectation

The WebUI setup packs should not silently mutate the system. Instead, one-click setup buttons should launch a structured Hermes task that:
1. inspects the environment
2. explains what will be installed or configured
3. performs the setup through the normal toolchain
4. reports what succeeded, what failed, and what needs approval

This keeps the feature broadly usable across different user machines and safer for GitHub distribution.

# 34 Real Odoo Read-Only Preflight Demo

**Status:** Next phase candidate
**Date:** May 19, 2026
**Relationship to v0.7:** A separate phase after the frozen Fake ERP MVP and safety-story layers.

## Purpose

This document defines a narrow possible v0.8 phase.

The goal is to connect to a real Odoo instance in read-only mode, map a real sales order into the canonical model, run Formula Guard, and show an auditable preflight result without performing any write action.

## Scope

The phase should include:

- a real Odoo read-only adapter;
- fetching a real sales order;
- mapping the order to the canonical `SalesOrder` model;
- running Formula Guard in preflight mode;
- returning an auditable result in the API and demo story.

## Out Of Scope

This phase must not include:

- confirming sales orders;
- creating or updating Odoo records;
- a full approval workflow;
- browser-extension capture;
- MCP gateway work;
- business memory;
- LLM-based agent builder behavior;
- marketplace publishing;
- a broad universal ERP connector.

## Why This Is The Right Next Step

This phase keeps the next expansion small and defensible.

It proves that the current MVP can connect to real ERP data in read-only form before any write capability is considered.

That is a safer transition than jumping directly from the Fake ERP MVP into full automation.

## Acceptance Criteria

The phase is successful if:

- a real Odoo sales order can be read;
- the order can be mapped to the canonical model;
- Formula Guard can be evaluated;
- the result can be shown in the API or `/demo`;
- no real ERP writes are performed.

## No-Goals

This document does not change runtime behavior.

It does not add endpoints, adapters, persistence tables, or UI code.

It only records the next phase candidate so the project boundary stays clear.
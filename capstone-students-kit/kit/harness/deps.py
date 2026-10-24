from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional
from .backends import AccountDB, Ledger, TicketStore
from .retriever import BaselineRetriever
from .llm import RuleLLM


@dataclass
class Deps:
    llm: object
    db: AccountDB
    ledger: Ledger
    tickets: TicketStore
    retriever: Callable[..., list]
    user_role: str = "support_agent"


def make_deps(role: str = "support_agent", llm=None, retriever=None) -> Deps:
    db = AccountDB()
    return Deps(llm=llm or RuleLLM(), db=db, ledger=Ledger(db), tickets=TicketStore(),
                retriever=retriever or BaselineRetriever(), user_role=role)

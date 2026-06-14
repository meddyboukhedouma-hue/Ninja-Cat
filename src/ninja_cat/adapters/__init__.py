"""Adapters — implémentations concrètes des ports, branchées au monde extérieur.

Le cœur (moteur, doctrine) n'importe **jamais** ce sous-paquet directement ; il
ne dépend que des interfaces de ports (cf. `ninja_cat.memory.MemoryPort`). Les
adapters peuvent, eux, parler à des services externes (CLI, réseau, fichiers).
"""

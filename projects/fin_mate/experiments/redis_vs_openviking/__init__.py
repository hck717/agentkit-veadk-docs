"""E3 Redis vs OpenViking：同一 pipeline、不同 DB（vector + sparse）。
3 pipes（hybrid / advanced / hyde_rrf）× 2 backends（OpenViking / Redis）= 6 configs，
用同一 nomic-embed-text 768d（Ollama），唯一變數係 DB。
"""

from mcp.server.mcpserver import MCPServer
from search import compare_revisions

mcp = MCPServer("revision-grounding-eval")


@mcp.tool()
def search_regulation(query: str, top_k: int = 3) -> list[dict]:
    """
    Sök i 14 CFR Part 107 (2017 vs 2021) och returnera de mest relevanta
    paragraferna, med en 'changed'-flagga som visar om paragrafen ändrats
    mellan versionerna.

    Använd det här toolet INNAN du citerar en regel eller paragraf, så att
    du inte råkar ge en föråldrad eller felaktig regel med korrekt
    källhänvisning men fel sakinnehåll.

    Args:
        query: Frågan i klartext, t.ex. "night flying rules" eller
               "remote pilot certificate age requirement".
        top_k: Antal resultat att returnera (default 3).

    Returns:
        Lista med dicts, ett per matchande paragraf:
        {
            "section": "§ 107.29",
            "text_2017": "...",
            "text_2021": "...",
            "changed": true,
            "change_note": "kort beskrivning av vad som faktiskt ändrades,
                             om känt — annars null"
        }
    """
    results = compare_revisions(query, k=top_k)
    for r in results:
        if r.get("changed") and r.get("change_note") is None:
            r["change_note"] = (
                "Flaggad som ändrad, men ingen detaljerad diff tillgänglig — "
                "verifiera manuellt innan citering."
            )
    return results


@mcp.tool()
def check_section_validity(section: str) -> dict:
    """
    Slå upp en specifik paragraf (t.ex. "§ 107.53") och visa om den
    betyder samma sak 2017 som 2021, eller om paragrafnumret återanvänts
    för ett helt annat ämne.

    Args:
        section: Paragrafbeteckning, t.ex. "§ 107.53".

    Returns:
        {
            "section": "§ 107.53",
            "same_topic": false,
            "topic_2017": "Applicability (subpart C intro)",
            "topic_2021": "ADS-B Out prohibition",
            "warning": "Paragrafnumret är återanvänt för ett helt annat ämne."
        }
    """
    raise NotImplementedError


if __name__ == "__main__":
    mcp.run()

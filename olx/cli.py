import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import client

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Search OLX Portugal from the terminal.")
console = Console()


def _price(r):
    if r["price"] is None:
        return "-"
    s = f"€{r['price']:g}"
    if r["previous_price"]:
        s += f" [dim](was €{r['previous_price']:g})[/dim]"
    if r["negotiable"]:
        s += " [dim]neg[/dim]"
    return s


@app.command()
def search(
    query: str,
    min_price: Optional[float] = typer.Option(None, "--min", help="Minimum price in EUR"),
    max_price: Optional[float] = typer.Option(None, "--max", help="Maximum price in EUR"),
    condition: Optional[str] = typer.Option(None, "--condition", "-c", help="new or used"),
    near: Optional[str] = typer.Option(None, "--near", "-n", help="Town to search around, e.g. Porto or Lisboa"),
    radius: Optional[int] = typer.Option(None, "--radius", "-r", help="Km around --near (OLX allows 0-100)"),
    sort: Optional[str] = typer.Option(None, "--sort", "-s", help="new, cheap or dear (default: relevance)"),
    limit: int = typer.Option(50, "--limit", "-l"),
    loose: bool = typer.Option(False, "--loose", help="Keep OLX's fuzzy matches instead of requiring every word"),
    as_json: bool = typer.Option(False, "--json"),
):
    """Search listings."""
    if sort and sort not in client.SORTS:
        raise typer.BadParameter(f"--sort must be one of {', '.join(client.SORTS)}")
    if condition and condition not in ("new", "used"):
        raise typer.BadParameter("--condition must be new or used")
    try:
        rows, total, city = client.search(
            query, min_price=min_price, max_price=max_price, condition=condition, near=near,
            radius=radius, sort=sort, limit=limit, strict=not loose,
        )
    except client.OLXError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if as_json:
        print(json.dumps([{k: v for k, v in r.items() if k != "description"} for r in rows], ensure_ascii=False, indent=2))
        return

    if not rows:
        # OLX pads empty searches with unrelated listings, so its total isn't a match count.
        console.print(f"No listings with “{query}” in the title" + ("" if loose else " (try --loose)") + ".")
        return

    where = f" near {city['name']}" + (f" (+{radius} km)" if radius else "") if city else ""
    t = Table(title=f"{len(rows)} matches (OLX returned {total}) for “{query}”{where}", show_lines=False)
    t.add_column("Price", no_wrap=True)
    t.add_column("Title", overflow="fold")
    t.add_column("Cond.", no_wrap=True)
    t.add_column("Where", overflow="fold", max_width=22)
    t.add_column("Listed", no_wrap=True)
    t.add_column("ID", no_wrap=True, style="dim")
    for r in rows:
        flags = (" [cyan]biz[/cyan]" if r["business"] else "") + (" [green]ship[/green]" if r["courier"] else "")
        t.add_row(_price(r), f"[link={r['url']}]{r['title']}[/link]{flags}", r["condition"] or "-",
                  r["city"] or "-", r["created"], str(r["id"]))
    console.print(t)


@app.command()
def show(ref: str = typer.Argument(..., help="Listing id or URL"), as_json: bool = typer.Option(False, "--json")):
    """Show one listing in full."""
    try:
        r = client.offer(ref)
    except client.OLXError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return
    console.print(f"[bold]{r['title']}[/bold]  {_price(r)}")
    console.print(f"{r['condition'] or '-'} · {r['city']}, {r['region']} · listed {r['created']} · seller {r['seller']}"
                  + (" (business)" if r["business"] else "") + (" · ships via OLX" if r["courier"] else ""))
    console.print(r["url"], style="dim")
    console.print()
    console.print((r["description"] or "").replace("<br />", "").strip())


def main():
    app()

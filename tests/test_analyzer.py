from pathlib import Path

from autoplay.analyzer import ModeAnalyzer
from autoplay.parser import parse_aff_chart


SAMPLES = Path(__file__).parent / "samples"


def _sample(name: str) -> str:
    return (SAMPLES / name).read_text(encoding="utf-8")


def test_mode_analyzer_builds_segments() -> None:
    content = _sample("basic_6k_scenecontrol.aff")
    chart = parse_aff_chart(content, designant_choice=True)
    analyzer = ModeAnalyzer()
    analyzer.analyze_chart_for_6k(content, chart)

    sky = analyzer.get_sky_segments()
    ground = analyzer.get_ground_segments()

    assert sky
    assert ground
    assert any(mode == "6k" for _, _, mode in sky)
    assert any(mode == "6k" for _, _, mode in ground)

# 도트 그림 데이터 테스트 (QA팀이 더한 부품 테스트, 2026-11-19 사장 지시 "픽셀 아트").
# 스프라이트 격자·색표가 올바른지, 얼굴이 계급마다 부위별로 하나씩 최산으로 바뀌는지 확인한다.
# (1단계의 디더링 테스트 3개는 사장 지시로 "부위별 바뀌기" 테스트로 바꿨다)
import pytest

import pixel_art as pa
from symbols import RANKS

RANK_T = dict(RANKS)


def test_sprite_rows_same_length():
    """모든 스프라이트의 격자 줄 길이가 같다."""
    for name, (rows, _) in pa.all_sprites().items():
        assert len({len(r) for r in rows}) == 1, name


def test_sprite_chars_in_palette():
    """격자에 색표에 없는 글자가 없다 ("."은 투명)."""
    for name, (rows, colors) in pa.all_sprites().items():
        used = {ch for r in rows for ch in r} - {pa.CLEAR}
        assert used <= set(colors), (name, used - set(colors))


def test_generated_frames_and_scene_valid():
    """코드로 만드는 판·배경도 줄 길이와 색표가 맞다."""
    for rows, colors in [pa.wood_frame(85, 27), pa.wood_frame(28, 11, inner="W"), pa.scene(lanes=(85,), field_x=143)]:
        pa.check_sprite(rows, colors)


def test_check_sprite_rejects_bad_grids():
    with pytest.raises(ValueError):
        pa.check_sprite(["KK", "K"], {"K": "#000000"})
    with pytest.raises(ValueError):
        pa.check_sprite(["KZ"], {"K": "#000000"})


def test_face_layers_same_size():
    """두 얼굴의 부위 4개는 모두 같은 크기(20×22)라 서로 바꿔 끼워도 자리가 맞는다."""
    for face in (pa.SEONGJAE, pa.CHOISAN):
        assert set(face["layers"]) == set(pa.PART_ORDER)
        for part, rows in face["layers"].items():
            assert len(rows) == pa.FACE_H and {len(r) for r in rows} == {pa.FACE_W}, part


def test_parts_t0_is_seongjae():
    """t=0(이병)이면 부위·점·색이 성재 얼굴과 정확히 같다."""
    assert pa.choisan_parts(0) == []
    assert pa.blend_face(0) == pa.whole_face(pa.SEONGJAE)


def test_parts_t1_is_choisan():
    """t=1(하사)이면 부위·점·색이 최산 얼굴과 정확히 같다."""
    assert pa.choisan_parts(1) == pa.PART_ORDER
    assert pa.blend_face(1) == pa.whole_face(pa.CHOISAN)


def test_parts_per_rank_monotonic():
    """계급이 오를수록 최산 부위가 줄지 않고, 단계마다 바뀌는 부위가 정해져 있다."""
    expected = {"이병": [], "일병": ["hair"], "상병": ["hair", "eyes"], "병장": ["hair", "eyes", "shape"],
                "하사": ["hair", "eyes", "shape", "skin"]}
    got = {name: pa.choisan_parts(t) for name, t in RANKS}
    assert got == expected
    counts = [len(got[name]) for name, _ in RANKS]
    assert counts == sorted(counts)
    for (_, a), (_, b) in zip(RANKS, RANKS[1:]):              # 이전 단계의 최산 부위는 다음 단계에도 남는다
        assert set(pa.choisan_parts(a)) <= set(pa.choisan_parts(b))


def test_eyes_and_mouth_stages_change_only_their_cells():
    """상병(눈썹·눈)·하사(입·피부) 단계에서 달라진 점은 그 부위 칸 안에만 있다.
    (머리·얼굴형은 다른 부위를 덮거나 드러내는 부위라 칸 비교 대신 위 부위 목록으로 확인)"""
    for prev, now, part in [("일병", "상병", "eyes"), ("병장", "하사", "skin")]:
        rows_a, _ = pa.blend_face(RANK_T[prev])
        rows_b, _ = pa.blend_face(RANK_T[now])
        cells = {(x, y) for face in (pa.SEONGJAE, pa.CHOISAN) for y, r in enumerate(face["layers"][part])
                 for x, ch in enumerate(r) if ch != pa.CLEAR}
        changed = {(x, y) for y, (ra, rb) in enumerate(zip(rows_a, rows_b))
                   for x, (ca, cb) in enumerate(zip(ra, rb)) if ca != cb}
        assert changed and changed <= cells, (part, changed - cells)


def test_choisan_eyes_have_pupils_and_strands_end_above_brows():
    """하사 얼굴: 눈동자 점이 있고(감은 눈처럼 보이지 않게), 앞머리 2가닥은 눈썹 줄 위에서 끝난다."""
    eyes = pa.CHOISAN["layers"]["eyes"]
    assert sum(r.count("P") for r in eyes) >= 4
    brow_top = min(y for y, r in enumerate(eyes) if "B" in r)
    strands = pa.strand_pieces(pa.CHOISAN["layers"]["hair"])
    assert len(strands) == 2
    for (_, y0, _, y1) in strands:
        assert y1 <= brow_top


def test_hero_has_podium_under_feet():
    """박산 아래에 나무 지휘대가 있고, 지휘대는 몸보다 넓다."""
    rows, _ = pa.PODIUM, pa.WOOD_COLORS
    assert len(rows[0]) > len(pa.HERO_TORSO[0])


def test_enemy_by_wave():
    """1~2웨이브 슬라임, 3~5 고블린, 6부터 해골 병사."""
    assert [pa.enemy_kind(w) for w in (1, 2, 3, 5, 6, 40)] == ["slime", "slime", "goblin", "goblin",
                                                                 "skeleton", "skeleton"]


def test_photo_cached_and_kept(tk_root):
    """이미지는 창(Tk)마다 한 번만 만들고 캐시가 참조를 붙잡는다. 투명 칸은 투명, 배율대로 커진다."""
    pa.clear_cache()
    calls = []

    def build():
        calls.append(1)
        return ["K.", ".K"], {"K": "#112233"}
    a = pa.photo(tk_root, "test", build, scale=3)
    b = pa.photo(tk_root, "test", build, scale=3)
    assert a is b and len(calls) == 1
    assert a in pa._CACHE.values()
    assert str(a) in tk_root.tk.call("image", "names")
    assert (a.width(), a.height()) == (6, 6)
    assert a.transparency_get(4, 0) and not a.transparency_get(0, 0)
    assert a.get(0, 0) == (0x11, 0x22, 0x33)
    pa.clear_cache()

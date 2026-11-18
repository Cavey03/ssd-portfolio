"""Tests for mission_control.localllm parsing helpers."""

from __future__ import annotations

import unittest

from mission_control.localllm import (
    GpuInfo,
    InstalledModel,
    LoadedModel,
    parse_nvidia_smi,
    parse_ps,
    parse_tags,
    parse_timestamp,
)

TAGS_SAMPLE = (
    '{"models":[ '
    '{"name":"ornith-1.5:9b","size":6550813657,'
    '"details":{"parameter_size":"9.0B","quantization_level":"Q4_K_M"}}, '
    '{"name":"gemma4:12b","size":8021618941,'
    '"details":{"parameter_size":"11.9B","quantization_level":"Q4_K_M"}}'
    ']}'
)

PS_SAMPLE = (
    '{"models":[{'
    '"name":"ornith-1.5:9b","size":7682517892,'
    '"size_vram":7682517892,"context_length":65536,'
    '"expires_at":"2026-11-18T13:11:50.080476753+02:00"'
    '],'
    ']}'
)

PS_EMPTY = '{"models":[]}'


class ParseTagsTests(unittest.TestCase):
    def test_parses(self):
        models = parse_tags(TAGS_SAMPLE)
        self.assertEqual(len(models), 2)
        # sorted by name: gemma4:12b first
        self.assertIsInstance(models[0], InstalledModel)
        self.assertEqual(models[0].name, "gemma4:12b")
        self.assertEqual(models[0].size_bytes, 8021618941)
        self.assertEqual(models[0].parameter_size, "11.9B")
        self.assertEqual(models[0].quantization, "Q4_K_M")
        self.assertEqual(models[1].name, "ornith-1.5:9b")
        self.assertEqual(models[1].size_bytes, 6550813657)
        self.assertEqual(models[1].parameter_size, "9.0B")
        self.assertEqual(models[1].quantization, "Q4_K_M")

    def test_invalid_json_raises(self):
        with self.assertRaises(ValueError):
            parse_tags("not json")

    def test_models_not_list_raises(self):
        with self.assertRaises(ValueError):
            parse_tags('{"models": 3}')

    def test_skips_entry_without_name(self):
        text = (
            '{"models":['
            '{"name":"ornith-1.5:9b","size":100,'
            '"details":{"parameter_size":"9.0B","quantization_level":"Q4_K_M"}},'
            '{"size":200},'
            '"notadict"}'
            ']}'
        )
        models = parse_tags(text)
        self.assertEqual([m.name for m in models], ["ornith-1.5:9b"])


class ParsePsTests(unittest.TestCase):
    def test_parses(self):
        models = parse_ps(PS_SAMPLE)
        self.assertEqual(len(models), 1)
        self.assertIsInstance(models[0], LoadedModel)
        model = models[0]
        self.assertEqual(model.name, "ornith-1.5:9b")
        self.assertEqual(model.size_bytes, 7682517892)
        self.assertEqual(model.vram_bytes, 7682517892)
        self.assertEqual(model.context_length, 65536)
        self.assertEqual(model.gpu_percent, 100)
        self.assertIsNotNone(model.expires_at)
        self.assertEqual(model.expires_at.hour, 13)
        self.assertEqual(model.expires_at.microsecond, 80476)

    def test_empty(self):
        self.assertEqual(parse_ps(PS_EMPTY), ())


class ParseTimestampTests(unittest.TestCase):
    def test_nanoseconds(self):
        ts = parse_timestamp("2026-11-18T13:11:50.080476753+02:00")
        self.assertIsNotNone(ts)
        self.assertEqual(ts.year, 2026)
        self.assertEqual(ts.month, 11)
        self.assertEqual(ts.day, 18)
        self.assertEqual(ts.hour, 13)
        self.assertEqual(ts.minute, 11)
        self.assertEqual(ts.second, 50)
        self.assertEqual(ts.microsecond, 80476)

    def test_z_suffix(self):
        ts = parse_timestamp("2026-11-18T11:00:00Z")
        self.assertIsNotNone(ts)
        self.assertEqual(ts.tzinfo, __import__("datetime").timezone.utc)
        self.assertEqual(ts.hour, 11)

    def test_none(self):
        self.assertIsNone(parse_timestamp(None))

    def test_int(self):
        self.assertIsNone(parse_timestamp(42))

    def test_garbage(self):
        self.assertIsNone(parse_timestamp("garbage"))


class ParseNvidiaSmiTests(unittest.TestCase):
    def test_sample(self):
        info = parse_nvidia_smi("NVIDIA GeForce RTX 5070, 9351, 12227, 18")
        self.assertIsInstance(info, GpuInfo)
        self.assertEqual(info.name, "NVIDIA GeForce RTX 5070")
        self.assertEqual(info.memory_used_mb, 9351)
        self.assertEqual(info.memory_total_mb, 12227)
        self.assertEqual(info.utilization_percent, 18)

    def test_na(self):
        info = parse_nvidia_smi("NVIDIA GeForce RTX 5070, 9351, 12227, [N/A]")
        self.assertIsInstance(info, GpuInfo)
        self.assertIsNone(info.utilization_percent)

    def test_empty(self):
        self.assertIsNone(parse_nvidia_smi(""))

    def test_garbage(self):
        self.assertIsNone(parse_nvidia_smi("garbage"))


if __name__ == "__main__":
    unittest.main()

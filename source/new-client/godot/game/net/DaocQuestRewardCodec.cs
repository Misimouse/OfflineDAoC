using System;
using System.Collections.Generic;

namespace MMOEngine;

public partial class DaocClient
{
    // Inactive until the gateway/UI and original-server roundtrip are verified.
    // PacketLib194.SendQuestWindow + virtual PacketLib1124.WriteItemData.
    public sealed class QuestRewardDialog1127
    {
        public int Code, QuestId, GiverId, Data3, Data4, DialogType, Wrap;
        public string Name = "", Summary = "", Story = "";
        public string[] Goals = Array.Empty<string>();
        public uint Money;
        public int ExperiencePercent, RequiredChoices;
        public byte[][] FixedItemRecords = Array.Empty<byte[]>();
        public byte[][] OptionalItemRecords = Array.Empty<byte[]>();
    }

    static bool TryQuestPascal(Reader reader, out string value)
    {
        value = "";
        if (reader.Left < 1 || reader.Left < 1 + reader.At(0)) return false;
        value = reader.Pascal(); return true;
    }

    public static bool TryReadQuestRewardDialog1127(Reader reader, out QuestRewardDialog1127 value)
    {
        value = null;
        if (reader == null || reader.Left < 12 || reader.Byte() != 0) return false;
        var result = new QuestRewardDialog1127 { Code = reader.Byte() };
        if (result.Code != 0x21 && result.Code != 0x22) return false;
        result.QuestId = reader.Short(); result.GiverId = reader.Short();
        result.Data3 = reader.Short(); result.Data4 = reader.Short();
        result.DialogType = reader.Byte(); result.Wrap = reader.Byte();
        if (result.QuestId == 0 || result.GiverId == 0 || result.Wrap > 1 ||
            result.DialogType != (result.Code == 0x22 ? 2 : 1)) return false;
        if (!TryQuestPascal(reader, out result.Name) || result.Name.Length == 0 ||
            !TryQuestPascal(reader, out result.Summary) || reader.Left < 2) return false;
        int storyBytes = reader.Short();
        if (reader.Left < storyBytes + 3) return false;
        result.Story = reader.FixedRaw(storyBytes);
        if (reader.Short() != result.QuestId) return false;
        int goalCount = reader.Byte(); result.Goals = new string[goalCount];
        for (int i = 0; i < goalCount; i++)
            if (!TryQuestPascal(reader, out result.Goals[i])) return false;
        if (reader.Left < 6) return false;
        result.Money = reader.Int(); result.ExperiencePercent = reader.Byte();
        int fixedCount = reader.Byte(); result.FixedItemRecords = new byte[fixedCount][];
        for (int i = 0; i < fixedCount; i++)
            if (!TryReadTradeItemRecord1124(reader, out result.FixedItemRecords[i])) return false;
        if (reader.Left < 2) return false;
        result.RequiredChoices = reader.Byte();
        int optionCount = reader.Byte();
        if (result.RequiredChoices > 8 || result.RequiredChoices > optionCount) return false;
        result.OptionalItemRecords = new byte[optionCount][];
        for (int i = 0; i < optionCount; i++)
            if (!TryReadTradeItemRecord1124(reader, out result.OptionalItemRecords[i])) return false;
        if (reader.Left != 0) return false;
        value = result; return true;
    }

    public static bool TryBuildQuestOfferResponse(QuestRewardDialog1127 dialog, bool accept, out byte[] payload)
    {
        payload = Array.Empty<byte>();
        if (dialog == null || dialog.Code != 0x22 || dialog.DialogType != 2 ||
            dialog.QuestId < 1 || dialog.QuestId > ushort.MaxValue ||
            dialog.GiverId < 1 || dialog.GiverId > ushort.MaxValue) return false;
        // Quest offers use the original DialogResponse QuestSubscribe code;
        // echoing the incoming window code0x22 has no handler in DOL.
        var writer = new Writer(); writer.Short((ushort)dialog.QuestId);
        writer.Short((ushort)dialog.GiverId); writer.Short(0);
        writer.Byte(0x64); writer.Byte(accept ? (byte)1 : (byte)0); writer.Short(0);
        payload = writer.ToArray(); return true;
    }

    // Original QuestRewardChosen (wire0xE8). This only encodes a request;
    // quest eligibility, reward ownership and completion belong to DOL.
    public static bool TryBuildQuestRewardChoice(QuestRewardDialog1127 dialog, int[] choices, out byte[] payload)
    {
        payload = Array.Empty<byte>(); choices ??= Array.Empty<int>();
        if (dialog == null || dialog.Code != 0x21 || dialog.DialogType != 1 ||
            dialog.QuestId < 1 || dialog.QuestId > ushort.MaxValue ||
            dialog.GiverId < 1 || dialog.GiverId > ushort.MaxValue ||
            dialog.OptionalItemRecords == null || dialog.OptionalItemRecords.Length > byte.MaxValue ||
            dialog.RequiredChoices < 0 || dialog.RequiredChoices > 8 ||
            choices.Length != dialog.RequiredChoices) return false;
        var seen = new HashSet<int>();
        foreach (int index in choices)
            if (index < 0 || index >= dialog.OptionalItemRecords.Length || !seen.Add(index)) return false;
        var writer = new Writer(); writer.Byte(1); writer.Byte((byte)choices.Length);
        for (int i = 0; i < 8; i++) writer.Byte(i < choices.Length ? (byte)choices[i] : (byte)0);
        writer.Short(0); writer.Short(0); writer.Short(0);
        writer.Short((ushort)dialog.QuestId); writer.Short((ushort)dialog.GiverId);
        payload = writer.ToArray(); return true;
    }
}

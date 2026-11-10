using System;

namespace MMOEngine;

public partial class DaocClient
{
    // PacketLib1109.SendTradeWindow with virtual PacketLib1124.WriteItemData.
    // Keep item records intact for the existing ReadItem decoder. No inventory
    // ownership or acceptance outcome is inferred from this packet.
    public sealed class TradeWindow1127
    {
        public bool Closed;
        public byte[] OwnSlots = Array.Empty<byte>();
        public int[] OwnMoney = Array.Empty<int>();
        public int[] PartnerMoney = Array.Empty<int>();
        public bool PartnerPresent, Repairing, Combining;
        public byte[][] PartnerItemRecords = Array.Empty<byte[]>();
        public string Title = "";
    }

    public static bool TryReadTradeWindow1127(Reader r, out TradeWindow1127 value)
    {
        value = null;
        if (r.Left == 40)
        {
            for (int i = 0; i < 40; i++) if (r.At(i) != 0) return false;
            r.Skip(40); value = new TradeWindow1127 { Closed = true }; return true;
        }
        if (r.Left < 41) return false;
        var result = new TradeWindow1127 { OwnSlots = new byte[10], OwnMoney = new int[5], PartnerMoney = new int[5] };
        for (int i = 0; i < 10; i++)
        {
            byte slot = r.Byte(); result.OwnSlots[i] = slot;
            if (slot != 0) for (int j = 0; j < i; j++) if (result.OwnSlots[j] == slot) return false;
        }
        if (r.Short() != 0) return false;
        for (int i = 0; i < 5; i++) result.OwnMoney[i] = r.Short();
        if (r.Short() != 0) return false;
        for (int i = 0; i < 5; i++) result.PartnerMoney[i] = r.Short();
        if (r.Short() != 0) return false;
        int count = r.Byte(), present = r.Byte(), repair = r.Byte(), combine = r.Byte();
        if (count > 10 || present > 1 || repair > 1 || combine > 1 || (present == 0 && count != 0)) return false;
        result.PartnerPresent = present == 1; result.Repairing = repair == 1; result.Combining = combine == 1;
        result.PartnerItemRecords = new byte[count][];
        for (int i = 0; i < count; i++)
        {
            if (!TryReadTradeItemRecord1124(r, out var record)) return false;
            for (int j = 0; j < i; j++) if (result.PartnerItemRecords[j][0] == record[0]) return false;
            result.PartnerItemRecords[i] = record;
        }
        if (r.Left < 1 || r.Left != 1 + r.At(0)) return false;
        result.Title = r.Pascal(); value = result; return true;
    }

    static bool TryReadTradeItemRecord1124(Reader r, out byte[] record)
    {
        record = Array.Empty<byte>();
        // Slot + fixed prefix through flags. The optional spell descriptions
        // precede the effect ushort and the final Pascal item name.
        if (r.Left < 25) return false;
        int flags = r.At(21), cursor = 22;
        foreach (int mask in new[] { 0x08, 0x10 })
        {
            if ((flags & mask) == 0) continue;
            if (r.Left < cursor + 3) return false;
            int length = r.At(cursor + 2); cursor += 3 + length;
            if (r.Left < cursor) return false;
        }
        cursor += 2;
        if (r.Left <= cursor) return false;
        cursor += 1 + r.At(cursor);
        if (r.Left < cursor) return false;
        record = new byte[cursor];
        for (int i = 0; i < cursor; i++) record[i] = (byte)r.At(i);
        r.Skip(cursor); return true;
    }

    // Original ModifyTrade payload only. Sending, session guards, ownership and
    // any confirmed result belong to the gateway/server integration.
    public static bool TryBuildPlayerTradeRequest(int action, int[] slots, int[] money, out byte[] payload)
    {
        payload = Array.Empty<byte>();
        if (action < 0 || action > 2) return false;
        var writer = new Writer();
        if (action != 1)
        {
            if ((slots != null && slots.Length != 0) || (money != null && money.Length != 0)) return false;
            writer.Byte((byte)action); writer.Byte(0); writer.Byte(0); writer.Byte(0);
            payload = writer.ToArray(); return true;
        }
        if (slots == null || slots.Length > 10 || money == null || money.Length != 5) return false;
        for (int i = 0; i < slots.Length; i++)
        {
            if (slots[i] != 0 && (slots[i] < 40 || slots[i] > 79)) return false;
            if (slots[i] != 0) for (int j = 0; j < i; j++) if (slots[j] == slots[i]) return false;
        }
        foreach (int denomination in money) if (denomination < 0 || denomination > 65535) return false;
        writer.Byte(1); writer.Byte(0); writer.Byte(0); writer.Byte(0);
        for (int i = 0; i < 10; i++) writer.Byte(i < slots.Length ? (byte)slots[i] : (byte)0);
        writer.Short(0); foreach (int denomination in money) writer.Short((ushort)denomination);
        payload = writer.ToArray(); return true;
    }
}

using System;
using DOL.GS.PacketHandler;

namespace DOL.GS.Commands
{
    public static class BridgeGmCombatMode
    {
        public const string ActiveKey = "DAoCBridge.CombatTest";
        public const string ResponsePrefix = "[DAOC_BRIDGE_GM] ";
        public static bool Enabled(GamePlayer player) => player != null && player.TempProperties.GetProperty<bool>(ActiveKey);
        public static bool AllowsNpcAttack(GamePlayer player, bool npcAttacker, bool playerControlledAttacker)
            => AllowsNpcAttack(Enabled(player), npcAttacker, playerControlledAttacker);
        public static bool AllowsNpcAttack(bool enabled, bool npcAttacker, bool playerControlledAttacker)
            => enabled && npcAttacker && !playerControlledAttacker;
    }

    [CmdAttribute("&bridgegm", ePrivLevel.GM, "Temporary protected GM / real NPC combat test",
        "/bridgegm protected", "/bridgegm combat", "/bridgegm status")]
    public sealed class BridgeGmCommandHandler : AbstractCommandHandler, ICommandHandler
    {
        public void OnCommand(GameClient client, string[] args)
        {
            GamePlayer player = client?.Player;
            if (player == null) return;
            string mode = args.Length == 2 ? args[1].ToLowerInvariant() : "status";
            if (mode == "protected")
            {
                player.TempProperties.RemoveProperty(BridgeGmCombatMode.ActiveKey);
                player.attackComponent.StopAttack();
                player.Stealth(true);
            }
            else if (mode == "combat")
            {
                if (!player.IsAlive || player.IsInvulnerableToAttack ||
                    player.TempProperties.GetProperty<bool>(FlyCommandHandler.ActiveKey))
                {
                    DisplayMessage(client, "Leave observer flight and wait until alive without temporary immunity before testing combat.");
                    DisplayMessage(client, BridgeGmCombatMode.ResponsePrefix + (BridgeGmCombatMode.Enabled(player) ? "combat" : "protected"));
                    return;
                }
                player.TempProperties.SetProperty(BridgeGmCombatMode.ActiveKey, true);
                player.Stealth(false);
            }
            else if (mode != "status")
            {
                DisplaySyntax(client);
                return;
            }
            // Temporary player state only: never modify/save account privileges.
            DisplayMessage(client, BridgeGmCombatMode.ResponsePrefix + (BridgeGmCombatMode.Enabled(player) ? "combat" : "protected"));
        }
    }
}

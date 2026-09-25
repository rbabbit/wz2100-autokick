# Warzone 2100 — Not-Ready → Spectators

## Handover / implementation notes

**Date:** 26 September 2026  
**Tested Warzone version:** 4.7.0  
**Status:** **Working in an isolated live lobby test. Global rollout to every production host has NOT been completed.**

---

## 1. What this changes

Warzone 2100 normally supports:

```text
Player stays Not Ready too long
→ host auto-kicks player completely out of the lobby
```

The tested modification changes this to:

```text
Player stays Not Ready too long
→ player is "kicked to Spectators"
→ player stays connected to the same lobby
→ player can later move back to Players
→ player can Ready normally and play
```

The final wording intentionally uses **"kicked to Spectators"** rather than "moved to Spectators".

---

## 2. Confirmed working behaviour

This was tested in a real waiting lobby.

Confirmed:

- A human player joined as a normal player.
- The player deliberately did not press Ready.
- After the configured timeout the player was moved to Spectators.
- The connection was NOT closed.
- The player remained in the same lobby.
- The player could later move themselves back to Players.
- The player could then press Ready normally.
- The lobby remained functional.

This is the important result: **the full player flow works.**

---

## 3. Exact tested binary

Experimental binary:

```text
/srv/sunshine-player-dev/bin/warzone2100-notready-spec-test
```

SHA-256 of the final tested V3 binary:

```text
3c42548f8dd23a499e574a21db9142cf76171effcb05a84833967c572c5061fa
```

The test host reported:

```text
Warzone 2100 - Headless Mode
Version: 4.7.0
Built: 2026-09-25
```

The hash above is the exact executable used for the final successful test.

---

## 4. Global deployment status

A later attempt was made to install the tested binary at:

```text
/usr/bin/warzone2100
```

The deployment script first verified the exact expected hash:

```text
Expected: 3c42548f8dd23a499e574a21db9142cf76171effcb05a84833967c572c5061fa
Actual:   3c42548f8dd23a499e574a21db9142cf76171effcb05a84833967c572c5061fa
PASS: exact tested V3 binary confirmed
```

It then copied the binary, but the production-data-path check failed:

```text
FAIL: production Warzone data not found
ROLLED BACK
```

Therefore:

**Do not assume the modification is installed globally.**

The next step is to audit the exact executable and `--datadir` used by each production host family before replacing anything.

---

## 5. VPS / build environment used

Server:

```text
Ubuntu 24.04
2 logical CPUs
AMD EPYC-Milan Processor
2.8 GiB RAM
2.0 GiB swap
```

Source tree:

```text
/srv/sunshine-player-dev/source/warzone2100
```

Important source files:

```text
/srv/sunshine-player-dev/source/warzone2100/src/multiplay.cpp
/srv/sunshine-player-dev/source/warzone2100/src/multiint.cpp
/srv/sunshine-player-dev/source/warzone2100/src/hci/quickchat.cpp
```

Experimental build tree:

```text
/srv/sunshine-player-dev/build-notready-spec-test
```

Experimental game-data tree:

```text
/srv/sunshine-player-dev/build-notready-spec-test/data
```

SDL3 prefix:

```text
/srv/sunshine-player-dev/sdl3
```

Known-good stock binary that was deliberately not replaced during testing:

```text
/srv/sunshine-player-dev/bin/warzone2100-stock
```

Known-good Phase6 snapshot:

```text
/srv/sunshine-player-dev/snapshots/Phase6-KNOWN-GOOD-20260819
```

---

## 6. Build configuration recovered from the VPS

The known-good CMake cache showed:

```text
CMAKE_BUILD_TYPE=RelWithDebInfo
CMAKE_INSTALL_PREFIX=/usr/local
CMAKE_PREFIX_PATH=/srv/sunshine-player-dev/sdl3
CMAKE_GENERATOR=Ninja
```

Relevant options included:

```text
BUILD_EXAMPLES=OFF
BUILD_SHARED_LIBS=OFF
BUILD_STATIC_LIB=ON
BUILD_TESTING=ON
BUILD_TESTS=OFF
BUILD_TOOLS=OFF
ENABLE_DISCORD=OFF
ENABLE_DOCS=ON
ENABLE_GNS_NETWORK_BACKEND=ON
ENABLE_ICE=ON
ENABLE_NLS=ON
WZ_ENABLE_WARNINGS=OFF
WZ_ENABLE_WARNINGS_AS_ERRORS=ON
WZ_DOWNLOAD_PREBUILT_PACKAGES=ON
WZ_ENABLE_BACKEND_VULKAN=ON
WZ_ENABLE_BASIS_UNIVERSAL=ON
WZ_FORCE_MINIMAL_OPUSFILE=ON
WZ_INCLUDE_TERRAIN_HIGH=ON
WZ_USE_STACK_PROTECTION=ON
```

The experimental tree was configured with:

```bash
cmake \
  -S /srv/sunshine-player-dev/source/warzone2100 \
  -B /srv/sunshine-player-dev/build-notready-spec-test \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_PREFIX_PATH=/srv/sunshine-player-dev/sdl3 \
  -DCMAKE_INSTALL_PREFIX=/usr/local \
  -DENABLE_DISCORD=OFF \
  -DBUILD_EXAMPLES=OFF \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_TESTS=OFF \
  -DBUILD_TOOLS=OFF \
  -DWZ_ENABLE_WARNINGS=OFF \
  -DWZ_DOWNLOAD_PREBUILT_PACKAGES=ON
```

---

## 7. Important source/API compatibility detail

Do not blindly copy code from a newer Warzone branch into this 4.7.0 tree.

During the first build attempt the patch treated the result of:

```cpp
NETmovePlayerToSpectatorOnlySlot(...)
```

as an optional and called:

```cpp
.has_value()
.value()
```

That failed to compile on this source tree:

```text
error: request for member 'has_value' in 'newSpectatorIdx',
which is of non-class type 'bool'
```

For this build, use a boolean:

```cpp
bool movedToSpectators =
    NETmovePlayerToSpectatorOnlySlot(i, false);
```

---

## 8. Why `hostOverride=false` is essential

This is the most important behavioural detail.

Warzone internally tracks people who were forcibly moved to Spectators by the host.

The netplay code has host-moved tracking equivalent to:

```text
identitiesMovedToSpectatorsByHost
ipsMovedToSpectatorsByHost
```

When the player is moved using host override / `byHost=true`, their IP and identity are recorded.

Later, when that spectator tries to return themselves to Players, Warzone checks that host-moved record and can refuse the move.

This happened in the first successful spectator test:

```text
timeout
→ moved to Spectators
→ stayed connected
→ could NOT return to Players
```

The final fix was:

```cpp
NETmovePlayerToSpectatorOnlySlot(i, false);
```

The `false` is intentional.

Final tested behaviour:

```text
automatic Ready timeout
→ NON-punitive spectator move
→ player stays connected
→ player can later return to Players
```

Manual host moderation can remain separate and keep normal Warzone host-punishment semantics.

---

## 9. Core final behaviour

The important final logic in `src/multiplay.cpp` is conceptually:

```cpp
std::string timedOutPlayerName = getPlayerName(i);

bool movedToSpectators =
    NETmovePlayerToSpectatorOnlySlot(i, false);

if (!movedToSpectators && NETopenNewSpectatorSlot())
{
    movedToSpectators =
        NETmovePlayerToSpectatorOnlySlot(i, false);
}

if (movedToSpectators)
{
    std::string notice = astringf(
        "Auto-kicking player (%s) to Spectators because they waited too long "
        "to check Ready. They can rejoin Players when ready.",
        timedOutPlayerName.c_str());

    sendRoomSystemMessage(notice.c_str());

    resetReadyStatus(true);
}
else
{
    std::string failureNotice = astringf(
        "No spectator slot was available for %s. "
        "Removing player from the lobby.",
        timedOutPlayerName.c_str());

    sendRoomSystemMessage(failureNotice.c_str());

    kickPlayer(
        i,
        "You have been removed from the room.\n"
        "No spectator slot was available after the Ready timeout.",
        ERROR_CONNECTION,
        false);
}
```

Behaviour:

1. Try an existing spectator slot.
2. If no spectator slot is available, attempt to open one.
3. Retry the move.
4. If successful, keep the player connected.
5. Reset lobby Ready state normally.
6. If spectator placement genuinely cannot be performed, fall back to a real kick.

---

## 10. Why the original messages stayed wrong

The first working spectator build still showed text such as:

```text
Players who don't check Ready in time will be kicked.
Player will be kicked if they don't check Ready soon.
Auto-kicking player...
```

The behaviour was already correct, but the text was not.

Reason:

Warzone's original Not-Ready warnings are sent as localized quick-chat message contexts such as:

```text
PlayerShouldCheckReadyNotice
NotReadyKickWarning
NotReadyKicked
```

The receiving player's own stock client renders those localized strings.

Therefore changing the host's `quickchat.cpp` alone does not guarantee that an unmodified remote client sees new wording.

The final V3 approach sends ordinary host/system messages instead of using the stock localized kick message contexts for this feature.

Relevant existing Warzone functions:

```cpp
sendRoomSystemMessage(...)
sendRoomSystemMessageToSingleReceiver(...)
```

This makes the new wording visible to normal unmodified clients.

---

## 11. Final message design

Initial lobby notice:

```text
NOTICE: Please check Ready so the game can begin
Players who don't check Ready in time will be kicked to Spectators.
You can rejoin Players when ready.
```

Private warning shortly before timeout:

```text
NOTICE: If you don't check Ready soon, you will be kicked to Spectators.
You can rejoin Players when ready.
```

Public warning:

```text
Player will be kicked to Spectators if they don't check Ready soon: NAME
```

Final timeout:

```text
Auto-kicking player (NAME) to Spectators because they waited too long
to check Ready. They can rejoin Players when ready.
```

The user tested the final wording/behaviour and confirmed it worked.

---

## 12. Countdown warning implementation

The stock implementation begins warning repeatedly close to the timeout.

The V3 test changed this to a single host-side warning around 5 seconds before timeout.

Concept:

```cpp
else if (!NetPlay.players[i].ready &&
         totalSecondsNotReady == (NotReadyAutoKickSeconds - 5))
{
    std::string personalWarning =
        "NOTICE: If you don't check Ready soon, you will be kicked to "
        "Spectators. You can rejoin Players when ready.";

    sendRoomSystemMessageToSingleReceiver(
        personalWarning.c_str(),
        i);

    if (!isBlindSimpleLobby(game.blindMode))
    {
        std::string publicWarning = astringf(
            "Player will be kicked to Spectators if they don't check "
            "Ready soon: %s",
            getPlayerName(i));

        sendRoomSystemMessage(publicWarning.c_str());
    }
}
```

---

## 13. Initial Ready notice implementation

The stock code around `PlayerShouldCheckReadyNotice` was replaced in the test host path with normal room text.

Concept:

```cpp
auto autoNotReadyKickSeconds = war_getAutoNotReadyKickSeconds();

std::string readyNotice;

if (isBlindSimpleLobby(game.blindMode))
{
    readyNotice = "NOTICE: Please check Ready";
}
else
{
    readyNotice = "NOTICE: Please check Ready so the game can begin";
}

if (autoNotReadyKickSeconds > 0)
{
    readyNotice +=
        "\nPlayers who don't check Ready in time will be kicked to "
        "Spectators. You can rejoin Players when ready.";
}

sendRoomSystemMessage(readyNotice.c_str());
```

---

## 14. One integration concern before production rollout

The stock final auto-kick block also emitted:

```text
WZEVENT: notready-kick: ...
```

The experimental V3 replacement removed the entire stock final kick block, including that command-interface event.

Before rolling this out everywhere, check whether any production controller, recorder, admin page, analytics process, or replay pipeline depends on:

```text
WZEVENT: notready-kick
```

If something depends on it, either:

- preserve the old event for compatibility even though the player is now moved to Spectators, or
- introduce a new event such as `notready-spec` and update the consumers.

Do not ignore this during a global deployment audit.

---

## 15. Test profile

Isolated test profile:

```text
/srv/wzhost/NotReadySpecTest
```

Test port:

```text
2151
```

RBot +33 was stopped during testing so that port 2151 was free.

Test timeout:

```text
hostAutoNotReadyKickSeconds=20
```

Production hosts may use a different timeout, commonly 45 seconds.

---

## 16. Correct experimental launch

The first launch failed because no game-data directory was specified:

```text
fatal: Could not find game data. Aborting.
```

The corrected host used the explicit experimental data tree:

```bash
/srv/sunshine-player-dev/bin/warzone2100-notready-spec-test \
  --datadir=/srv/sunshine-player-dev/build-notready-spec-test/data \
  --configdir=/srv/wzhost/NotReadySpecTest \
  --autohost=rbot-dedicated.json \
  --gameport=2151 \
  --portmapping=false \
  --headless \
  --nosound
```

---

## 17. Safe incremental rebuild on this VPS

The VPS has only two logical CPUs.

A build using `-j2` saturated both CPUs with processes such as `basisu` and `cc1plus`.

The later rebuilds used one CPU and low priority:

```bash
taskset -c 1 \
nice -n 19 \
ionice -c 3 \
cmake --build /srv/sunshine-player-dev/build-notready-spec-test \
  --target warzone2100 \
  -j1
```

This is much safer on this server.

---

## 18. Source restoration

The experimental workflow backed up the normal source files before patching and restored them after the binary was built.

The final build output confirmed:

```text
PASS: normal source restored
```

Therefore the current normal source tree should **not** be assumed to contain V3.

Likely V3 backup directory pattern:

```text
/root/notready-spec-v3-YYYYMMDD-HHMMSS/
```

Other related test backup patterns:

```text
/root/notready-spec-*
/root/notready-spec-fix-*
/root/notready-spec-return-v2-*
```

---

## 19. Production families to audit before global rollout

Known relevant host/service families on this VPS include:

```text
rbot-dedicated.service
rbot-player.service
sunshine-game-rotation.service
sunshine-pool.service
tourney1v1.service
opa5v5.service
sunshine-bot1v1.service
emag-ffa.service
```

Do not confuse actual game hosts with history/web/recorder services such as:

```text
rbot-public.service
sunshine-web.service
tourney-web.service
```

For every real host family, determine:

1. Which Warzone executable it actually launches.
2. Which `--datadir` it uses.
3. Which config/profile directory it uses.
4. Whether it sets `hostAutoNotReadyKickSeconds`.
5. Whether it provides spectator slots.
6. Whether any controller parses the old `notready-kick` event.
7. Whether it has its own copied Warzone executable rather than `/usr/bin/warzone2100`.

Only after that audit should the feature be deployed globally.

---

## 20. What NOT to do

Do **not**:

- blindly replace every `warzone2100` executable;
- assume all hosts use `/usr/bin/warzone2100`;
- assume all hosts use the same data directory;
- overwrite the known-good stock binary;
- build inside the Phase6 known-good snapshot;
- use `hostOverride=true` for the automatic Not-Ready move;
- rely only on changing `quickchat.cpp` for remote-client wording;
- remove fallback kick behaviour when spectator placement genuinely fails;
- deploy without checking whether production tooling depends on `WZEVENT: notready-kick`.

---

## 21. Recommended production implementation

For a clean upstream-quality implementation, consider making the behaviour configurable rather than permanently changing the meaning of `hostAutoNotReadyKickSeconds`.

For example:

```text
hostAutoNotReadyKickSeconds=45
hostAutoNotReadyAction=spectate
```

Possible actions:

```text
kick
spectate
```

That would preserve existing Warzone behaviour by default while allowing dedicated hosts to opt into the new behaviour.

The tested prototype did not add this configuration key; it directly changed the Not-Ready action in the experimental build.

---

## 22. Final proven state

The tested sequence was:

```text
Join Players
→ remain Not Ready
→ warning says player will be kicked to Spectators
→ timeout expires
→ player is moved to Spectators
→ player remains connected
→ player manually moves back to Players
→ move is accepted
→ player can Ready normally
```

**This sequence was confirmed working.**

---

## 23. Exact final binary checksum again

```text
SHA256:
3c42548f8dd23a499e574a21db9142cf76171effcb05a84833967c572c5061fa

File:
/srv/sunshine-player-dev/bin/warzone2100-notready-spec-test
```

That is the reference build for this work.

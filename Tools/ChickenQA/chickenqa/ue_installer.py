"""Generate source-only Unreal Automation smoke tests without changing gameplay code."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


class InstallError(ValueError):
    pass


@dataclass(frozen=True)
class InstallTarget:
    project: Path
    module: str
    header: Path
    cpp: Path


def locate_target(project: Path, module: str | None = None) -> InstallTarget:
    project = project.resolve()
    if not project.is_file() or project.suffix.lower() != '.uproject':
        raise InstallError(f'Could not find a .uproject file: {project}')
    try:
        project_data = json.loads(project.read_text(encoding='utf-8-sig'))
    except (ValueError, OSError) as exc:
        raise InstallError(f'Cannot read project metadata: {exc}') from exc
    modules = [item.get('Name') for item in project_data.get('Modules', [])
               if isinstance(item, dict) and isinstance(item.get('Name'), str)]
    if module:
        if module not in modules:
            raise InstallError(f'Module {module!r} not declared in .uproject: {modules}')
        modules = [module]
    if not modules:
        raise InstallError('No C++ module in .uproject. This kit requires a C++ game project.')
    candidates: list[InstallTarget] = []
    for name in modules:
        module_dir = project.parent / 'Source' / name
        if not module_dir.is_dir():
            continue
        if not (module_dir / f'{name}.Build.cs').is_file():
            continue
        for header in module_dir.rglob('ChickenCharacter.h'):
            # Avoid accidentally installing in a different class/module.
            contents = header.read_text(encoding='utf-8-sig', errors='replace')
            if re.search(r'\bclass\s+(?:\w+_API\s+)?AChickenCharacter\s*:\s*public\s+ACharacter\b', contents):
                cpp = module_dir / 'Private' / 'Tests' / 'ChickenQASmokeTests.cpp'
                candidates.append(InstallTarget(project, name, header, cpp))
    if len(candidates) == 0:
        raise InstallError('AChickenCharacter : public ACharacter declaration was not found in the declared module(s). No files changed.')
    if len(candidates) > 1:
        raise InstallError('Multiple AChickenCharacter headers found; specify --module. No files changed.')
    return candidates[0]


def render_cpp(target: InstallTarget) -> str:
    """CDO configuration tests, not physics / knockdown behavior tests."""
    class_path = f'/Script/{target.module}.ChickenCharacter'
    return f'''// ChickenQA v0.4. Generated for {target.module}.
// Only inspects the native ChickenCharacter class default object (CDO).
// Does NOT test actual movement, push physics, network replication or knockdown.
#include "CoreMinimal.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/CapsuleComponent.h"
#include "UObject/UObjectGlobals.h"

namespace ChickenQATests
{{
    static ACharacter* GetChickenDefault(FAutomationTestBase& Test)
    {{
        UClass* Class = StaticLoadClass(ACharacter::StaticClass(), nullptr, TEXT("{class_path}"));
        if (!Class)
        {{
            Test.AddError(TEXT("Native ChickenCharacter UClass not found"));
            return nullptr;
        }}
        ACharacter* DefaultCharacter = Cast<ACharacter>(Class->GetDefaultObject());
        if (!DefaultCharacter)
        {{
            Test.AddError(TEXT("ChickenCharacter class default object is not an ACharacter"));
        }}
        return DefaultCharacter;
    }}
}}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FChickenQAClassRegistered,
    "ChickenQA.Character.ClassRegistered",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FChickenQAClassRegistered::RunTest(const FString& Parameters)
{{
    ACharacter* Character = ChickenQATests::GetChickenDefault(*this);
    TestNotNull(TEXT("Native ChickenCharacter default object"), Character);
    return Character != nullptr;
}}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FChickenQAMovementComponent,
    "ChickenQA.Character.MovementComponentReady",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FChickenQAMovementComponent::RunTest(const FString& Parameters)
{{
    const ACharacter* Character = ChickenQATests::GetChickenDefault(*this);
    if (!Character) return false;
    const UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
    TestNotNull(TEXT("CharacterMovementComponent"), Movement);
    if (!Movement) return false;
    TestTrue(TEXT("MaxWalkSpeed is finite and nonnegative"),
        FMath::IsFinite(Movement->MaxWalkSpeed) && Movement->MaxWalkSpeed >= 0.0f);
    TestTrue(TEXT("JumpZVelocity is finite"), FMath::IsFinite(Movement->JumpZVelocity));
    TestTrue(TEXT("GravityScale is finite"), FMath::IsFinite(Movement->GravityScale));
    return true;
}}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FChickenQACapsuleConfigured,
    "ChickenQA.Character.CapsuleConfigured",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FChickenQACapsuleConfigured::RunTest(const FString& Parameters)
{{
    const ACharacter* Character = ChickenQATests::GetChickenDefault(*this);
    if (!Character) return false;
    const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
    TestNotNull(TEXT("CapsuleComponent"), Capsule);
    if (!Capsule) return false;
    const float Radius = Capsule->GetUnscaledCapsuleRadius();
    const float HalfHeight = Capsule->GetUnscaledCapsuleHalfHeight();
    TestTrue(TEXT("Capsule radius is finite and positive"), FMath::IsFinite(Radius) && Radius > 0.0f);
    TestTrue(TEXT("Capsule half-height is finite and >= radius"),
        FMath::IsFinite(HalfHeight) && HalfHeight >= Radius);
    return true;
}}
#endif // WITH_DEV_AUTOMATION_TESTS
'''


def install_tests(target: InstallTarget, apply: bool) -> str:
    content = render_cpp(target)
    if target.cpp.exists():
        existing = target.cpp.read_text(encoding='utf-8-sig')
        if existing == content:
            return f'Already installed (unchanged): {target.cpp}'
        raise InstallError(f'Target file already exists with different content; refusing overwrite: {target.cpp}')
    if not apply:
        return f'DRY RUN: would create {target.cpp} (no files changed)'
    target.cpp.parent.mkdir(parents=True, exist_ok=True)
    target.cpp.write_text(content, encoding='utf-8-sig')
    return f'Installed: {target.cpp}'

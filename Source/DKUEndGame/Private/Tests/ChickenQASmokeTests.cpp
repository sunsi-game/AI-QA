// ChickenQA v0.4. Generated for DKUEndGame.
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
{
    static ACharacter* GetChickenDefault(FAutomationTestBase& Test)
    {
        UClass* Class = StaticLoadClass(ACharacter::StaticClass(), nullptr, TEXT("/Script/DKUEndGame.ChickenCharacter"));
        if (!Class)
        {
            Test.AddError(TEXT("Native ChickenCharacter UClass not found"));
            return nullptr;
        }
        ACharacter* DefaultCharacter = Cast<ACharacter>(Class->GetDefaultObject());
        if (!DefaultCharacter)
        {
            Test.AddError(TEXT("ChickenCharacter class default object is not an ACharacter"));
        }
        return DefaultCharacter;
    }
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FChickenQAClassRegistered,
    "ChickenQA.Character.ClassRegistered",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FChickenQAClassRegistered::RunTest(const FString& Parameters)
{
    ACharacter* Character = ChickenQATests::GetChickenDefault(*this);
    TestNotNull(TEXT("Native ChickenCharacter default object"), Character);
    return Character != nullptr;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FChickenQAMovementComponent,
    "ChickenQA.Character.MovementComponentReady",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FChickenQAMovementComponent::RunTest(const FString& Parameters)
{
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
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FChickenQACapsuleConfigured,
    "ChickenQA.Character.CapsuleConfigured",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FChickenQACapsuleConfigured::RunTest(const FString& Parameters)
{
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
}
#endif // WITH_DEV_AUTOMATION_TESTS

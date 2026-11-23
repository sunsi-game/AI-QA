#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Character/ChickenCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

// 테스트는 경계 상태만 주입하고 실제 게임 함수를 호출한다.
struct FChickenQAGameplayAccess
{
    static void Forward(AChickenCharacter& C) { C.MoveForward(1.f); }
    static void Failure(AChickenCharacter& C, FVector2D Body, FVector2D Visual)
    {
        C.BodyTilt = Body;
        C.VisualBodyTilt = Visual;
        C.UpdateBalanceFailure();
    }
};

namespace
{
    struct FTestWorld
    {
        UWorld* World = UWorld::CreateWorld(EWorldType::Game, false);
        ~FTestWorld() { if (World) World->DestroyWorld(false); }
        AChickenCharacter* Spawn(FVector Position = FVector::ZeroVector)
        {
            if (!World) return nullptr;
            FActorSpawnParameters Params;
            Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            auto* C = World->SpawnActor<AChickenCharacter>(Position, FRotator::ZeroRotator, Params);
            if (C)
            {
                C->SetRoundInputEnabled(true);
                // BeginPlay 없는 임시 월드에서도 AddImpulse의 활성 조건을 충족한다.
                C->GetCharacterMovement()->Activate(true);
                C->GetCharacterMovement()->bRunPhysicsWithNoController = true;
                // 바닥과 중력을 분리하여 수평 이동을 관찰한다.
                C->GetCharacterMovement()->SetMovementMode(MOVE_Flying);
            }
            return C;
        }
        static void Step(AChickenCharacter& C)
        {
            C.GetCharacterMovement()->TickComponent(1.f / 60.f, LEVELTICK_All, nullptr);
        }
    };
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FChickenQAMovementBehavior, "ChickenQA.Gameplay.MovementAndInputGate",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FChickenQAMovementBehavior::RunTest(const FString& Parameters)
{
    FTestWorld Fixture;
    auto* C = Fixture.Spawn();
    if (!TestNotNull(TEXT("Character"), C)) return false;
    for (int I = 0; I < 30; ++I)
    {
        FChickenQAGameplayAccess::Forward(*C);
        FTestWorld::Step(*C);
    }
    TestTrue(TEXT("Input moves actor forward"), C->GetActorLocation().X > 10.f);
    TestTrue(TEXT("No sideways drift"), FMath::Abs(C->GetActorLocation().Y) < 1.f);
    C->SetRoundInputEnabled(false);
    const FVector Locked = C->GetActorLocation();
    FChickenQAGameplayAccess::Forward(*C);
    FTestWorld::Step(*C);
    TestTrue(TEXT("Disabled input produces no motion"), C->GetActorLocation().Equals(Locked, .01f));
    TestTrue(TEXT("Disabled input is not queued"), C->GetPendingMovementInputVector().IsNearlyZero());
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FChickenQACollisionBehavior, "ChickenQA.Gameplay.CollisionPushAndCooldown",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FChickenQACollisionBehavior::RunTest(const FString& Parameters)
{
    FTestWorld Fixture;
    auto* A = Fixture.Spawn();
    auto* B = Fixture.Spawn(FVector(200.f, 0.f, 0.f));
    if (!TestNotNull(TEXT("Attacker"), A) || !TestNotNull(TEXT("Receiver"), B)) return false;
    FHitResult Hit(B, B->GetCapsuleComponent(), B->GetActorLocation(), -FVector::ForwardVector);
    // 접촉 검출은 주입하되 충돌 응답과 이동 적분은 실제 구현을 실행한다.
    A->GetCharacterMovement()->Velocity = FVector(-300.f, 0.f, 0.f);
    A->MoveBlockedBy(Hit);
    FTestWorld::Step(*B);
    TestTrue(TEXT("Separating contact produces no velocity"), B->GetVelocity().IsNearlyZero());
    A->GetCharacterMovement()->Velocity = FVector(300.f, 0.f, 0.f);
    A->MoveBlockedBy(Hit);
    A->MoveBlockedBy(Hit);
    const FVector Before = B->GetActorLocation();
    FTestWorld::Step(*B);
    // 기본 0.8 배율의 단일 충격은 240cm/s이며 중복 처리 시 480cm/s가 된다.
    TestTrue(TEXT("Single push velocity, no duplicate impulse"), B->GetVelocity().X > 100.f && B->GetVelocity().X < 300.f);
    TestTrue(TEXT("Receiver position changes"), B->GetActorLocation().X > Before.X);
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FChickenQABalanceBehavior, "ChickenQA.Gameplay.BalanceFailureGates",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FChickenQABalanceBehavior::RunTest(const FString& Parameters)
{
    for (int Direction = 0; Direction < 4; ++Direction)
    {
        FTestWorld Fixture;
        auto* C = Fixture.Spawn();
        if (!TestNotNull(TEXT("Character"), C)) return false;
        const float Limit = C->GetBalanceFailureAngleDegrees() / 35.f;
        const FVector2D Tilts[] = {{Limit, 0}, {-Limit, 0}, {0, Limit}, {0, -Limit}};
        const ECFKnockdownDirection Expected[] = {ECFKnockdownDirection::Forward, ECFKnockdownDirection::Back,
            ECFKnockdownDirection::Left, ECFKnockdownDirection::Right};
        auto* M = C->GetCharacterMovement();
        M->SetMovementMode(MOVE_Walking);
        FChickenQAGameplayAccess::Failure(*C, Tilts[Direction] * .5, Tilts[Direction]);
        TestFalse(TEXT("Below internal limit survives"), C->IsFallen());
        FChickenQAGameplayAccess::Failure(*C, Tilts[Direction], FVector2D::ZeroVector);
        TestFalse(TEXT("Visual pose must reach limit"), C->IsFallen());
        M->SetMovementMode(MOVE_Falling);
        FChickenQAGameplayAccess::Failure(*C, Tilts[Direction], Tilts[Direction]);
        TestFalse(TEXT("Airborne limit is not elimination"), C->IsFallen());
        TestFalse(TEXT("Airborne balance does not queue elimination"), C->IsKnockdownPending());
        M->SetMovementMode(MOVE_Walking);
        M->PendingLaunchVelocity = FVector(0, 0, 350);
        FChickenQAGameplayAccess::Failure(*C, Tilts[Direction], Tilts[Direction]);
        TestFalse(TEXT("Pending launch survives"), C->IsFallen());
        M->PendingLaunchVelocity = FVector::ZeroVector;
        FChickenQAGameplayAccess::Failure(*C, Tilts[Direction], Tilts[Direction]);
        TestTrue(TEXT("Grounded visible limit eliminates immediately"), C->IsFallen());
        TestTrue(TEXT("Correct fall direction"), C->GetKnockdownDirection() == Expected[Direction]);
        TestTrue(TEXT("Fallen character stops"), M->MovementMode == MOVE_None && M->Velocity.IsNearlyZero());
        TestFalse(TEXT("Duplicate knockdown rejected"), C->StartKnockdown(Expected[Direction]));
    }
    return true;
}
#endif

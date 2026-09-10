"""Authored MVP content. Choice letters avoid ambiguous numeric string grading.

Five diagnostic categories per concept; three reserved study items per concept.
The original small seed remains supported. IDs are stable across fresh installs.
"""
from uuid import NAMESPACE_URL, uuid5

from app.questions.models import QuestionType as QT, ProblemSolvingSkill as PS

# Each row: stem (with units/assumptions), canonical choice, worked solution.
# Order: understanding, application, strategy, multi-step, transfer, study main,
# strategy probe, fresh verification. These are authored, not random templates.
BANK = {
    "PHY_VEC_001": [
        ("Which quantity is a vector? A: speed; B: displacement; C: mass; D: energy.", "B", "Displacement has magnitude and direction; speed, mass and energy are scalars."),
        ("A displacement is 3 m east then 4 m north. Its magnitude is: A: 7 m; B: 1 m; C: 5 m; D: 12 m.", "C", "Perpendicular components give sqrt(3^2+4^2)=5 m."),
        ("To add two forces at an arbitrary angle, choose the general method. A: add magnitudes; B: subtract magnitudes; C: resolve along common axes and add components; D: multiply magnitudes.", "C", "Components along the same axes add algebraically, then reconstruct the resultant."),
        ("Forces (6i+8j) N and (-3i-4j) N act together. Resultant magnitude: A: 5 N; B: 10 N; C: 15 N; D: 25 N.", "A", "The resultant is (3i+4j) N, with magnitude 5 N."),
        ("A boat moves north at 4 m/s relative to water; the current is east at 3 m/s. Ground speed: A: 1 m/s; B: 7 m/s; C: 5 m/s; D: 12 m/s.", "C", "Ground velocity is the vector sum of boat-relative-water and water-relative-ground velocities: sqrt(16+9)=5 m/s."),
        ("A drone flies 8 m east, 6 m north, then 8 m west. What is the magnitude of its displacement? A: 22 m; B: 10 m; C: 6 m; D: 14 m.", "C", "East and west components cancel. The net displacement is 6 m north, not the 22 m path length."),
        ("For a route with several legs, how should displacement be found? A: add all distances; B: add signed components and take the resultant magnitude; C: average speeds; D: multiply distances.", "B", "Track signed horizontal and vertical components separately. Path length is not displacement."),
        ("A robot moves 5 m east, 12 m north, then 10 m west. Displacement magnitude: A: 27 m; B: 17 m; C: 13 m; D: 7 m.", "C", "Net components are -5 m and 12 m; sqrt(25+144)=13 m."),
    ],
    "PHY_KIN_001": [
        ("The slope of a velocity-time graph represents: A: displacement; B: acceleration; C: distance; D: force.", "B", "Slope is change in velocity divided by elapsed time, which is acceleration."),
        ("A particle starts from rest with constant acceleration 2 m/s^2 for 3 s. Final speed: A: 3 m/s; B: 9 m/s; C: 6 m/s; D: 12 m/s.", "C", "With constant acceleration use v=u+at. Starting from rest gives v=0+2*3=6 m/s."),
        ("Constant acceleration is known, along with initial speed and displacement but not time. Which equation directly gives final speed? A: v=u+at; B: v^2=u^2+2as; C: s=ut; D: F=ma.", "B", "v^2=u^2+2as eliminates time for constant acceleration."),
        ("A car starts from rest, accelerates at 2 m/s^2 for 4 s, then keeps that speed for 3 s. Total distance: A: 16 m; B: 24 m; C: 40 m; D: 56 m.", "C", "First segment: s=0.5*2*16=16 m, v=8 m/s. Second: 8*3=24 m. Total 40 m."),
        ("A ball is released from rest inside a train moving at constant horizontal velocity. Ignoring air resistance, relative to the train it falls: A: straight down; B: backward; C: forward; D: upward.", "A", "The ball retains the train's horizontal velocity. Its horizontal relative velocity remains zero."),
        ("A cyclist starts from rest, accelerates at 3 m/s^2 for 2 s, then travels at constant speed for 4 s. Total distance: A: 6 m; B: 24 m; C: 30 m; D: 36 m.", "C", "Acceleration segment gives 6 m and final speed 6 m/s; constant-speed segment gives 24 m. Total 30 m."),
        ("For an accelerate-then-cruise journey, choose the valid setup. A: use the initial acceleration for the entire journey; B: split into segments and carry the final velocity into the next; C: multiply total time by initial speed; D: use only the cruise distance.", "B", "Acceleration changes between segments; solve each interval with its own acceleration and continuous velocity."),
        ("A cart starts from rest, accelerates at 2 m/s^2 for 3 s, then cruises for 2 s. Total distance: A: 9 m; B: 12 m; C: 21 m; D: 30 m.", "C", "First distance is 9 m, final speed 6 m/s; second distance 12 m. Total 21 m."),
    ],
    "PHY_NLM_001": [
        ("A body moves at constant velocity in an inertial frame. Its net force is: A: zero; B: along velocity; C: opposite velocity; D: equal to its weight in every case.", "A", "Constant velocity means zero acceleration, so the vector sum of forces is zero."),
        ("A net horizontal force of 15 N acts on a 3 kg block. Acceleration: A: 45 m/s^2; B: 5 m/s^2; C: 12 m/s^2; D: 0.2 m/s^2.", "B", "Newton's second law uses the net force: a=F_net/m=15/3=5 m/s^2."),
        ("To find tension between two connected blocks pulled on a smooth surface, first: A: set tension equal to the applied force; B: find system acceleration, then isolate a block; C: divide force by one block's mass only; D: assume zero acceleration.", "B", "Internal tension cancels for the whole system. Use its acceleration in a single-block force equation."),
        ("Blocks of 3 kg and 2 kg are joined by a light taut string on a smooth horizontal surface. A 10 N force pulls the 3 kg block away from the 2 kg block. Tension: A: 10 N; B: 6 N; C: 4 N; D: 2 N.", "C", "System acceleration is 10/(3+2)=2 m/s^2. Tension alone accelerates the 2 kg block: T=2*2=4 N."),
        ("A 2 kg object rests on a scale in a lift accelerating upward at 2 m/s^2. Take g=10 m/s^2. Scale reading: A: 16 N; B: 20 N; C: 24 N; D: 4 N.", "C", "N-mg=ma gives N=m(g+a)=2*12=24 N."),
        ("A 4 kg block pulls a 2 kg block via a light taut string on a smooth floor. An 18 N horizontal force is applied to the 4 kg block away from the other block. Tension: A: 18 N; B: 12 N; C: 6 N; D: 3 N.", "C", "The two-block acceleration is 18/6=3 m/s^2. The 2 kg block is pulled only by tension: T=2*3=6 N."),
        ("In the two-block problem, which setup determines tension? A: T equals the external force; B: find a=F/(m1+m2), then use T=m_unpulled*a; C: T=(m1+m2)g; D: set a=0.", "B", "Choose the combined system for acceleration and the unpulled block for tension; these are different free-body diagrams."),
        ("A 3 kg block pulls a 1 kg block via a light taut string on a smooth floor. A 20 N force acts on the 3 kg block away from the other block. Tension: A: 20 N; B: 15 N; C: 5 N; D: 4 N.", "C", "a=20/(3+1)=5 m/s^2. The unpulled 1 kg block needs T=1*5=5 N."),
    ],
    "PHY_FRIC_001": [
        ("Static friction on a resting block is generally: A: always mu_s*N; B: zero in all cases; C: self-adjusting up to mu_s*N; D: always larger than the applied force.", "C", "Static friction balances the tangential tendency to move, up to its limiting value."),
        ("A 2 kg block slides on a horizontal surface with mu_k=0.2. Take g=10 m/s^2. Friction magnitude: A: 2 N; B: 4 N; C: 10 N; D: 20 N.", "B", "There is no vertical acceleration, so N=mg=20 N. Kinetic friction is f_k=mu_k*N=4 N."),
        ("To decide whether a resting block starts sliding under a horizontal force F, first compare F with: A: mu_s*N; B: its speed; C: its kinetic energy; D: mass alone.", "A", "Static friction can balance the applied horizontal force only up to mu_s*N."),
        ("A 2 kg block is already sliding right. A 10 N force acts right, mu_k=0.2, g=10 m/s^2. Acceleration: A: 5 m/s^2; B: 2 m/s^2; C: 3 m/s^2; D: 7 m/s^2.", "C", "N=20 N, friction=4 N left, net force=6 N right, a=6/2=3 m/s^2."),
        ("A crate stays at rest on a truck accelerating right on a horizontal road. Static friction on the crate acts: A: left; B: right; C: downward; D: zero.", "B", "The crate needs rightward acceleration with the truck; static friction provides that horizontal force."),
        ("A 5 kg crate is pulled horizontally by 10 N on a level floor. mu_s=0.4 and g=10 m/s^2. It is initially at rest. Actual friction: A: 20 N; B: 10 N; C: 4 N; D: zero.", "B", "Maximum static friction is 20 N, but only 10 N is needed to balance the pull. The crate remains at rest."),
        ("For a resting crate with an applied force below limiting static friction, use: A: f=mu_s*N regardless of force; B: f equals the applied tangential force; C: kinetic friction; D: zero friction.", "B", "The limiting value is a cap, not the actual friction unless the body is on the verge of slipping."),
        ("A 4 kg box rests on a level floor. mu_s=0.5, g=10 m/s^2, horizontal pull=12 N. Actual friction: A: 20 N; B: 8 N; C: 12 N; D: zero.", "C", "The cap is 20 N; friction adjusts to 12 N and prevents motion."),
    ],
    "PHY_WEP_001": [
        ("Work done by a force perpendicular to displacement is: A: positive; B: negative; C: zero; D: force times speed.", "C", "W=F*s*cos(theta); cos(90 degrees)=0."),
        ("A 2 kg body moves at 3 m/s. Kinetic energy: A: 3 J; B: 6 J; C: 9 J; D: 18 J.", "C", "Kinetic energy depends on the square of speed: K=0.5*m*v^2=0.5*2*9=9 J."),
        ("With friction present, which general relation connects net work and speed change? A: kinetic energy is always conserved; B: W_net=Delta K; C: momentum is always conserved; D: potential energy is always zero.", "B", "The work-energy theorem includes work by all forces, including dissipative friction."),
        ("A 2 kg block starts from rest. A 10 N horizontal force acts through 3 m while a constant 4 N friction opposes motion. Final kinetic energy: A: 30 J; B: 12 J; C: 18 J; D: 42 J.", "C", "Net work=(10-4)*3=18 J. Starting from rest, final K=18 J."),
        ("A small object slides without friction from rest down either of two differently shaped tracks with the same vertical drop h. Final speeds are: A: equal; B: greater on the longer track; C: greater on the shorter track; D: always zero.", "A", "Gravity does the same work mgh on each track; the normal force does no work. Thus v=sqrt(2gh) in both."),
        ("A 1 kg block starts from rest and is pulled 4 m by a 6 N horizontal force against constant 2 N friction. Final kinetic energy: A: 24 J; B: 8 J; C: 16 J; D: 32 J.", "C", "Applied work is 24 J, friction work is -8 J; Delta K=16 J."),
        ("When using work-energy with friction, choose the correct accounting. A: ignore friction; B: sum positive applied work and negative friction work; C: add friction magnitude as positive work; D: set Delta K to zero.", "B", "Work is signed according to force direction relative to displacement. Opposing friction does negative work."),
        ("A cart starts from rest and is pulled 5 m by an 8 N force against constant 3 N friction. Final kinetic energy: A: 40 J; B: 15 J; C: 25 J; D: 55 J.", "C", "Net work=(8-3)*5=25 J, equal to the gain in kinetic energy."),
    ],
}

KINDS = [QT.CONCEPTUAL, QT.APPLICATION, QT.FORMULA_RECALL, QT.MULTI_STEP,
         QT.TRANSFER, QT.MULTI_STEP, QT.FORMULA_RECALL, QT.MULTI_STEP]
SKILLS = [PS.UNDERSTANDING, PS.EXECUTION, PS.STRATEGY_SETUP, PS.EXECUTION,
          PS.EXECUTION, PS.EXECUTION, PS.STRATEGY_SETUP, PS.EXECUTION]


def content_id(code, index):
    return uuid5(NAMESPACE_URL, f"atlas/mechanics/mvp-v1/{code}/{index}")


def study_ids(code):
    return [content_id(code, i) for i in (5, 6, 7)]


RESERVED_IDS = {qid for code in BANK for qid in study_ids(code)}

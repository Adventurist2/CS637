"""Build the project report, talk notes, slide data and offline demo.

Requires completed run_extensions.py and audit_extensions.py outputs.
PowerPoint authoring uses the editable Artifact Session, not this PDF builder.
"""
from pathlib import Path
from html import escape
import json
import math
import re
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,Image,KeepTogether,Preformatted)
from run_extensions import ROOT,OUT,save_json,case_obj
from extensions import Evaluator,critical_group,metrics

DEST=ROOT/'output'
PDF=DEST/'pdf'/'SEQUIN_Group_Extensions_Full_Report.pdf'
NAVY='#183544';TEAL='#087F8C';ORANGE='#CF5C36';PURPLE='#6554A4'


def num(v,places=2): return f'{float(v):,.{places}f}'
def pct(v): return num(100*float(v))+'%'
def load(name): return json.loads((OUT/name).read_text(encoding='utf-8'))
def csv(name): return pd.read_csv(OUT/name,dtype={'case':str})


class Report:
    def __init__(self):
        for name,file in [('Arial','arial.ttf'),('Arial-Bold','arialbd.ttf')]:
            path=Path('C:/Windows/Fonts')/file
            if path.exists(): pdfmetrics.registerFont(TTFont(name,str(path)))
            else:
                from reportlab.pdfbase.pdfmetrics import Font
                pdfmetrics.registerFont(Font(name,'Helvetica-Bold' if 'Bold' in name else 'Helvetica','WinAnsiEncoding'))
        self.styles=getSampleStyleSheet()
        for name,size,leading,color in [('Normal',10.3,14.8,NAVY),('Heading1',20,25,NAVY),('Heading2',13,17,TEAL)]:
            s=self.styles[name];s.fontName='Arial-Bold' if name!='Normal' else 'Arial';s.fontSize=size;s.leading=leading;s.textColor=colors.HexColor(color)
        self.styles['Normal'].spaceAfter=8
        self.styles.add(ParagraphStyle(name='Small',fontName='Arial',fontSize=8.5,leading=11.5,textColor=colors.HexColor('#455763'),spaceAfter=6))
        self.styles.add(ParagraphStyle(name='Cell',fontName='Arial',fontSize=8.5,leading=11.2,textColor=colors.HexColor(NAVY)))
        self.styles.add(ParagraphStyle(name='Cover',fontName='Arial-Bold',fontSize=31,leading=38,textColor=colors.HexColor(NAVY),spaceAfter=22))
        self.story=[];self.md=[]
    def p(self,text,small=False):
        self.story.append(Paragraph(escape(text),self.styles['Small' if small else 'Normal']));self.md.append(text+'\n')
    def h(self,text): self.story.append(Paragraph(escape(text),self.styles['Heading2']));self.md.append('## '+text+'\n')
    def section(self,title):
        self.story += [PageBreak(),Paragraph(escape(title),self.styles['Heading1']),Spacer(1,12)];self.md.append('\n# '+title+'\n')
    def table(self,headers,rows,widths=None):
        data=[[Paragraph(escape(str(x)),self.styles['Cell']) for x in row] for row in [headers]+rows]
        width=A4[0]-104
        table=Table(data,colWidths=widths or [width/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#DCE8E8')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor(TEAL)),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#D5DDE0'))]))
        self.story += [table,Spacer(1,12)]
        self.md += ['| '+' | '.join(map(str,headers))+' |','| '+' | '.join(['---']*len(headers))+' |']
        self.md += ['| '+' | '.join(map(str,row))+' |' for row in rows];self.md.append('')
    def plot(self,name,height=225):
        image=Image(str(OUT/name));ratio=image.imageWidth/image.imageHeight
        width=min(A4[0]-104,height*ratio);height=width/ratio
        self.story += [image,Spacer(1,9)];image.drawWidth=width;image.drawHeight=height
        self.md.append(f'![{name}](../../results/extensions/{name})\n')
    def code(self,text):
        self.story += [Preformatted(text,ParagraphStyle(name='Code',fontName='Courier',fontSize=8,leading=11,spaceAfter=12))];self.md.append('```text\n'+text+'\n```\n')
    def build(self):
        PDF.parent.mkdir(parents=True,exist_ok=True)
        def footer(canvas,doc):
            canvas.saveState();canvas.setFont('Arial',8);canvas.setFillColor(colors.HexColor('#62747B'))
            canvas.drawString(52,26,'CS637  /  SEQUIN group reproduction and extensions')
            canvas.drawRightString(A4[0]-52,26,str(doc.page));canvas.restoreState()
        doc=SimpleDocTemplate(str(PDF),pagesize=A4,rightMargin=52,leftMargin=52,topMargin=48,bottomMargin=48,
                              title='SEQUIN: Group Reproduction and Three Evaluated Extensions',author='CS637 project')
        doc.build(self.story,onFirstPage=footer,onLaterPages=footer)
        (PDF.parent/'REPORT_SOURCE.md').write_text('\n'.join(self.md),encoding='utf-8')


def report():
    summary=load('summary.json');validation=load('validation.json');pc=load('priority_precision_comparison.json');examples=load('priority_examples.json')
    ps=csv('protection_summary.csv');ts=csv('timing_summary.csv');cs=csv('priority_precision_summary.csv')
    compatibility=load('default_compatibility.json');designs=load('defense_designs.json')
    r=Report();r.story += [Spacer(1,68),Paragraph('SEQUIN<br/>Group reproduction and three evaluated extensions',r.styles['Cover'])]
    r.p('Full project report for CS637');r.p('Paper explanation, implementation audit, experiments, limitations and future work')
    r.story += [Spacer(1,35)];r.h('Study provenance')
    r.p('Group repository: AlankritGupta584/sequin-python-reproduction. Upstream commit e03e8495fb67af50f00c52daa75908e34960f151. Local branch: extensions-study.')
    r.p('Prepared on 29 October 2026. All extension measurements in this report were recomputed using the group repository\'s SciPy defender. The earlier project\'s results were not relabelled as new experiments.')
    r.p('Selected paper: Andrew Chio, Russell Bent, Kaarthik Sundar and Nalini Venkatasubramanian. SEQUIN: A Network Science and Physics-based Approach to Identify Sequential N-k Attacks in Electric Power Grids. ACM/IEEE ICCPS 2025. DOI 10.1145/3716550.3722029. [1]')
    r.p('Evidence: complete CSV results, source/scenario hashes, exact small-instance outage tables, matched comparison probes, saved demonstrations and independent validation are included in the project folder.',True)
    r.section('1. Executive explanation')
    r.p('Imagine a power network as roads carrying electricity. Removing one road changes the routes and how much each power station must produce. If another road fails after the operator has adjusted, the result can differ from removing both roads together. SEQUIN searches for damaging orders of line failures using network clues and a constrained model of the operator\'s response.')
    r.p('The group already implemented this core idea in plain Python. The current work studies what an operator can do with that information: protect a limited set of lines, account for different response intervals, and give selected services a higher priority. These answer preparedness, timing and service-allocation questions respectively.')
    rows=[]
    for name in ('14','39'):
        for policy in ('robust-sequential','initial-flow'):
            a=ps[(ps.case==name)&(ps.budget==2)&(ps.policy_group==policy)].iloc[0]
            rows.append([name,policy,pct(a.shed_fraction),num(a.reduction_pp)+' pp'])
    r.table(['Case','q=2 protection','Mean test worst loss','Reduction vs no defense'],rows,[42,160,145,144])
    r.p('Protection improves the no-defense reference in these examples, but the scenario-based plan does not beat every baseline. Timing changes both the final MW loss and the time-weighted snapshot proxy. Priority policies can improve selected services, often by sacrificing other demand. The later sections report ties and adverse cases as well as gains.')
    r.p(f'The fresh suite contains {summary["rows"]["protection"]:,} protection rows, {summary["rows"]["timing"]:,} timing rows and {summary["rows"]["priority"]:,} priority rows. These are deterministic evaluations within a small number of demand scenarios, not that many independent experimental samples.')
    r.h('Reading route')
    r.p('Sections 2-4 explain the paper and code. Sections 5-6 establish model differences and experimental fairness. Sections 7-12 explain the three extensions and their results. Sections 13-17 cover correctness, conclusions, future work and reproduction.')
    r.section('2. What the paper contributes')
    r.h('Sequential N-k interdiction')
    r.p('N is the number of components in a network and k is the failure budget. Here only transmission lines fail. The attacker chooses an ordered sequence of distinct lines. After every failure, the defender redispatches generators and, if necessary, sheds demand. Failed lines and previously lost service remain lost. The attacker seeks the largest final load shed. [1, Section 3]')
    r.p('The operator is myopic: it optimizes the present response without knowing the next outage. This is different from solving one multi-period plan with perfect knowledge of future failures. The history matters because later ramp bounds depend on current generation and later service bounds depend on which demand has already been lost.')
    r.h('Physics and network science')
    r.p('The defender enforces a DC approximation of AC power flow, nodal power balance, branch ratings, generator limits and ramp allowances. DC here names a linearized power-flow approximation. It does not mean the benchmark is a physical DC grid. It neglects losses and voltage/reactive-power dynamics.')
    r.p('The paper\'s Guided Exploration uses high flow, branch/generator flexibility, transmission width and load density to shortlist candidates. It evaluates cut impact by solving a defender response and chooses promising continuations. Its impact-reasoning stage groups common ordered prefixes to expose where losses grow. The active group implementation uses the released-style top-flow shortlist rather than every property in the printed algorithm. [1, Algorithm 1; 2]')
    r.h('Why the search is difficult')
    r.p('m available lines create m!/(m-k)! ordered sequences. Case 14 has 20 lines: k=2 gives 380 sequences. Case 39 has 46 lines: k=2 gives 2,070, while k=3 already gives 91,080. Each prefix needs an optimization response. Network screening reduces search work but can miss damaging sequences.')
    r.p('The paper\'s main strength is combining outage order with a constrained operating response. Its exact numerical outcomes depend on modeling details, randomized inputs and the selection among equally good operator dispatches. Reproduction should separate those issues from the quality of the attack search.')
    r.section('3. The group model, from input to response')
    r.table(['Stage','Code','What it does'],[
        ['Read case','grid_model.load_case','Parses bus, generator, branch and cost matrices. Optional seeded perturbation multiplies positive Pd only.'],
        ['Initial operating point','grid_model.initial_state','Least-cost intact-grid DC LP using scipy.optimize.linprog.'],
        ['Choose failure','search_methods.py','Exact, greedy or guided logic selects a line or complete attack sequence.'],
        ['Operator response','grid_model.defend','A MILP maximizes served MW subject to the surviving network, ramp windows and optional shutdown.'],
        ['Carry state','search_methods.run_sequence','Passes generation and served load into the next round.'],
        ['Measure loss','grid_model.shed_pu','Divides lost MW by baseMVA. New extension exports use explicit MW.']],[75,145,271])
    r.h('Variables and constraints')
    r.p('The response model has bus angle theta, generator MW output p, binary generator switch z, served MW s at each bus, and MW flow f on each surviving line. Removing a line removes its flow-angle equation and its flow variable from the active-line formulation. One bus angle is fixed in each connected island.')
    r.code('f_ij = baseMVA / (x_ij * tap_ij)\n       * (theta_i - theta_j - phase_shift_ij)\nGeneration + fixed injections - served demand\n       = net outgoing flow\n0 <= s_i(new) <= s_i(previous)\nlow_g = max(0, previous_p_g - alpha * Pmax_g)\nhigh_g = min(Pmax_g, previous_p_g + alpha * Pmax_g)\nlow_g * z_g <= p_g <= high_g * z_g')
    r.p('A generator can either operate inside its current ramp window or shut off completely. Shutdown is recourse in this steady-state model, so an emergency switch-off can bypass a gradual downward ramp. The group recreates z every round and does not carry a no-restart constraint. A previously zero-output unit can therefore return within the next upward allowance. The paper describes persistent shutdown in Eq. 2f; that distinction is retained and disclosed.')
    r.section('4. Search methods and existing limitations')
    r.table(['Method','Selection rule','Scope'],[
        ['Exact simultaneous','Enumerate unordered sets and apply one defender response.','All sets at a tractable k; one response opportunity.'],
        ['Exact sequential','Enumerate ordered sequences, responding after each cut.','All ordered sequences at a tractable k.'],
        ['Greedy-FLOW','Remove the current largest absolute-flow line.','One selected continuation each round.'],
        ['Greedy-IMPACT','Evaluate every remaining line and choose largest immediate shed.','One-step loss optimization, no future lookahead.'],
        ['Guided','Try top-flow starts. Later evaluate cut impact only in the top-N current-flow shortlist.','Best of these guided paths, generally heuristic.'],
        ['Permutation','Enumerate orders of a specified line set.','All orders of that set, not all possible sets.']],[96,214,181])
    r.p('network_metrics.py computes generator flexibility, branch thermal margin, local load density and a greedy edge-disjoint-path width heuristic. The group\'s width routine is not a max-flow certificate. Its local density is not the paper\'s equal-width clustered density. The active guided search uses current flow and immediate cut impact, so the helper differences do not directly drive that shortlist.')
    r.p('run_tests.py is a reproduction experiment driver rather than a unit-test suite. check_results.py asserts specific error thresholds against released reference CSVs. The historical README and implementation notes make some exact-match claims, while the current driver tests broader cases with different accuracy thresholds. Fresh output should take precedence over historical prose.')
    r.p('Several original search paths skip None responses, and exact search iterates all branch rows even if a supplied future case has inactive lines. The new evaluator restricts failures to initially available lines and raises on failed response optimization. It adds complete ordered-prefix caching. Caching by the unordered failed set would be wrong because different failure orders can produce different dispatch and service states.')
    r.section('5. How this differs from the earlier project')
    r.table(['Aspect','Group reproduction','Earlier sequin package'],[
        ['Units and solver','MW, SciPy, dense rows','Per-unit, highspy, sparse rows'],
        ['Shutdown','Fresh generator binary each round','Persistent online state; no restart'],
        ['Dispatch ties','Single service objective by default','Service objective followed by economic tie-break'],
        ['MILP gap','Default HiGHS relative gap','Explicit 1e-8 relative gap'],
        ['Angles','Every angle in [-pi,pi] plus island reference','Branch difference bounds plus island reference'],
        ['Negative Pd','Fixed injection in every response','Curtailable, nonrecoverable injection after initialization'],
        ['Random draw','Positive Pd entries only','Factors for all buses and negative injections'],
        ['Main guided search','Top current-flow shortlist','Multiple properties, plus separate released-style method']],[98,196,197])
    r.p('Identical seed integers do not guarantee identical load vectors across these implementations because they consume random draws differently. The matched model comparison therefore uses no demand perturbation and reads exactly the same case files. The six supplied cases all have zero active shunts and zero quadratic cost terms, so those generic capability differences cannot explain the measured six-case discrepancies.')
    r.table(['Fixed attack','Group MW','Earlier MW'],[['Case 14: (3,1)','439.970','462.970'],['Case 39: (14,46)','2,093.920','2,093.920'],['Case 118: (104,97)','531.398','1,192.347'],['Case 240: (437,433,436)','21,933.806','21,937.294']])
    r.p('These are selected fixed-sequence probes, not an overall quality ranking. Initial generator dispatch agrees almost exactly on five cases. Case 60 has a maximum individual-generator difference of 720 MW. The comparison does not isolate a unique cause for that difference; dispatch degeneracy is a plausible contributor. The group cost-tie probe also changes MIP precision, so it cannot attribute every change solely to the tie-break.')
    r.p(f'Backward compatibility: {len(compatibility["probes"])} prefix-state probes compare the extended defender with the untouched source loaded from the upstream Git commit. The largest generation or served-load difference is {compatibility["max_state_difference_mw"]} MW. This is direct compatibility evidence for the tested probes, not every possible input.')
    r.section('6. Critique and evaluation design')
    r.table(['Limitation or practical gap','Implemented response','Remaining scope'],[
        ['Identifies vulnerability without selecting investment','Budgeted line protection and adaptive re-evaluation','Ideal protection, equal costs, small finite design set'],
        ['Fixed response epochs','Variable windows and equal decision opportunities','Snapshot proxy, no continuous ramp trajectory'],
        ['Total MW treats service types equally','Weighted and critical-first service policies','Synthetic priority groups, no real critical-facility data'],
        ['Heuristic attack search may miss harm','Complete pairs on small cases and shared targeted cohorts','Larger cases remain sampled worst-found results'],
        ['A nominal plan may fail under shifted conditions','Held-out seeds and demand/ramp stress','Small scenario ensemble, no stochastic guarantee'],
        ['DC steady states omit dynamics','Explicit assumptions and scoped conclusions','No AC, transient, relay or frequency validation']],[151,170,170])
    r.h('Fair comparisons')
    r.p('The group response engine supplies every extension solve. Protection uses design demand seeds 0,1,2 and tests on unseen seeds 100-104. Test outcomes never choose the plan. Timing freezes attack orderings before comparing spacing, horizon and simultaneous/sequential policies. Priority evaluates every policy on exactly the same sequence set and starts from the same economic dispatch.')
    r.p('A separate total-tight policy requests the same relative MIP gap as the new priority objectives. This checks whether apparent priority benefits survive a more precise aggregate-service reference. The original total-service results remain available to show continuity with the group code. Numerical precision can alter intermediate dispatches in a sequential problem, so its effects need not stay small at the final round. [3,4]')
    r.p('Statistics use demand scenarios as the unit. Five held-out seeds support descriptive paired bootstrap intervals, not broad significance claims. Thousands of deterministic attack rows do not become thousands of independent demand experiments. Groups at different fractions vary both count and membership and are not guaranteed nested.')
    r.section('7. Extension 1: scenario-aware protection')
    r.p('Practical question: if only q lines can be made resistant to the modeled failure, which ones should be chosen? The attacker then adapts to the remaining eligible lines. Protecting the original worst attack alone would miss replacement attacks, so every plan is evaluated against all eligible ordered pairs.')
    r.code('For design scenarios s and protected set P:\n  loss_s(P) = max loss_s(ordered outage a), a disjoint P\n  choose |P| = q to minimize max_s loss_s(P)/demand_s\nGreedy step:\n  evaluate every additional eligible protected line\n  minimize worst design fraction, then mean, then line ID')
    r.p('Complete k=2 outage tables store each ordered sequence and its group-model loss. Protection only changes outage eligibility, not a surviving sequence\'s physical constraints. Filtering rows containing protected lines is therefore equivalent to rerunning the finite eligible attack set under the same deterministic policy. Independent fresh exhaustive replay verifies this on held-out cases.')
    r.table(['Protocol','Settings'],[['Cases and outage budget','Cases 14 and 39, k=2; 380 and 2,070 ordered pairs per demand scenario.'],['Protection budgets','q=0,1,2,3; exact outer enumeration additionally at q<=2.'],['Design/test demands','+/-5% positive-Pd draws, design seeds 0/1/2, test seeds 100-104.'],['Baselines','20 random nested plans, mean initial flow, unweighted edge betweenness, single-scenario design, simultaneous-outage design, exact finite outer design.'],['Stress','Freeze nominal plans; ramp 0.025/0.1/0.5 and demand spread 0%/15%, seeds 100/101.']],[120,371])
    r.p('This is a course-project extension of SEQUIN, not a claim to invent defender-attacker-defender protection. The paper itself identifies ruggedization as future work and cites related interdiction-defense research. [1, Section 6]')
    r.section('8. Protection results and generalization')
    r.plot('protection.png',190)
    rows=[]
    for name in ('14','39'):
        for q in (0,1,2,3):
            values=[]
            for policy in ('robust-sequential','initial-flow','single-scenario','simultaneous-design','random'):
                a=ps[(ps.case==name)&(ps.budget==q)&(ps.policy_group==policy)].iloc[0];values.append(pct(a.shed_fraction))
            rows.append([name,str(q)]+values)
    r.table(['Case','q','Robust','Flow','Single','Sim design','Random'],rows,[35,25,86,86,86,86,87])
    r.p('Values are mean held-out scenario worst loss as a percentage of positive demand. Each random value first averages 20 plans within its demand seed. Smaller is better. The adaptive sequence may differ for every plan and scenario.')
    r.p('Case 14: the robust q=2 plan materially reduces loss relative to no protection and the flow baseline. At q=1 its held-out gain is absent, while the single-scenario plan does better on these test seeds. Case 39: flow does slightly better at q=2, while robust protection gains more at q=3. The scenarios and budgets therefore determine which design is best.')
    intervals=summary['protection_intervals']
    r.table(['Case','q','Mean reduction (pp)','Descriptive 95% bootstrap interval'],[[a['case'],a['budget'],num(a['reduction_pp']),f"[{num(a['bootstrap95_pp'][0])}, {num(a['bootstrap95_pp'][1])}]" ] for a in intervals if a['budget'] in (2,3)],[40,30,150,271])
    r.p('The interval resamples only five held-out demand seeds, with pairing against the corresponding no-protection loss. It describes this small synthetic sample and should not be presented as a certificate of real-grid performance.')
    r.section('9. Protection stress and design optimality')
    r.plot('stress.png',230)
    r.p(f'The robust plan loses more than flow protection in {summary["stress_robust_worse_than_flow"]} of {summary["stress_comparisons"]} feasible stress configuration cells. Its largest excess is {num(summary["stress_worst_excess_pp"])} percentage points. A positive point in the plot is a failure to outperform that baseline. Repeated zero-perturbation seeds have identical demands and are not independent draws.')
    r.p(f'Of {summary["rows"]["stress"]} requested policy rows, {summary["rows"]["stress_ok"]} are feasible-start evaluations and {summary["rows"]["stress_initial_infeasible"]} record initial infeasibility. The perturbed case-39 starting operating points cannot always supply all demand before any failure. No attack loss is fabricated for those cases, and the study does not resample until it finds an easier starting point.')
    gaps=[]
    for d in designs:
        if d['exact_design_objective'] is not None:
            gaps.append([d['case'],d['budget'],num(100*d['robust_design_objective'][0],4),num(100*d['exact_design_objective'][0],4),num(100*(d['robust_design_objective'][0]-d['exact_design_objective'][0]),6)])
    r.table(['Case','q','Greedy design %','Exact design %','Gap (pp)'],gaps,[40,30,130,130,161])
    r.p('Exact design means all protection sets at the shown budget, evaluated on the finite training scenarios and all finite outage pairs. It does not mean exact protection against every possible demand or dispatch tie. Greedy can tie this oracle on these small instances and still generalize differently from flow protection on held-out seeds.')
    r.p('Future improvement: include demand spread and response-speed uncertainty inside the design objective, rather than only stress-testing a plan trained at one ramp setting. Add realistic line-specific costs and imperfect hardening success before treating the plan as an investment recommendation.')
    r.section('10. Extension 2: response-window model')
    r.p('Practical question: does it matter how quickly failures arrive and how long the operator can respond? The paper uses fixed epochs. This extension scales each response\'s ramp allowance by its duration and holds the total observation horizon fixed when comparing event patterns.')
    r.table(['Pattern','Windows at H=15 minutes','Interpretation'],[['Even','5, 5, 5','Equal response windows.'],['Early cluster','1, 1, 13','Short early opportunities followed by a long final window.'],['Late cluster','13, 1, 1','Long initial response, then rapid later failures.']],[100,170,221])
    r.code('Reference: alpha = 0.1 over tau = 5 minutes\nDerived ramp rate: R_g = alpha * Pmax_g / tau\nWindow allowance: R_g * duration_j\nSnapshot MWh proxy: sum_j shed_MW_j * duration_j / 60')
    r.p('These rates derive from a declared dimensionless reference, not equipment measurements. The model solves the endpoint response and charges that endpoint loss for the whole window. It does not integrate a physical dispatch trajectory. The MWh result is therefore a response-then-hold snapshot unserved-energy proxy, not validated physical energy not served.')
    r.p('For each case and seed, the attack cohort contains all distinct permutations of the guided and flow-greedy k=3 line sets. Every spacing pattern and comparator replays that same cohort. Horizons are 7.5,15,30 minutes. Cases are 14,39,118 and demand seeds are 0,1,2.')
    r.p('The simultaneous comparator loses all selected lines in its first window but redispatches again in the other two windows. It therefore has the same total horizon, duration vector and three decisions as its sequential counterpart. This differs from the original one-shot simultaneous baseline and removes a confounding difference in the number of response opportunities.')
    r.section('11. Timing results and interpretation')
    r.plot('timing.png',250)
    selected=ts[(ts.horizon_minutes==15)&(~ts.simultaneous)]
    r.table(['Case','Pattern','Mean cohort-worst final loss','Mean cohort-worst snapshot proxy'],[[a.case,a.pattern,pct(a.final_shed_fraction),pct(a.snapshot_energy_fraction)] for a in selected.itertuples()],[40,70,190,191])
    r.p('For each demand seed, the analysis takes the maximum over the frozen sequence cohort, then averages those maxima across seeds. Final-loss and proxy-energy maxima may correspond to different sequences. They should not be described as a single representative worst event.')
    r.p('The time-weighted measure can improve even when final MW is worse. A damaging final state reached only in short late windows contributes less to this particular proxy than the same loss held through a long window. That is a metric interpretation, not evidence that more final load shedding is preferable.')
    r.p('Longer response windows permit more generator movement, but this myopic irreversible model does not guarantee monotone final-loss improvement: intermediate dispatch can change, shutdown/restart choices can change, and the sampled worst sequence can change. Causal conclusions should stay within the declared model and cohort.')
    r.section('12. Extension 3: critical-service policy')
    r.p('Practical question: if some loads represent services such as communication, water pumping or healthcare, should every MW receive the same importance? The benchmark does not label actual facilities. The extension selects reproducible synthetic groups of positive-demand buses with seed 17. These illustrate priority allocation without claiming to identify real hospitals.')
    r.table(['Policy','Operator objective','Meaning'],[['Total (original)','Maximize sum of served MW','Original group baseline and its solver defaults.'],['Total-tight','Same objective, MIP relative gap 1e-8','Numerical control matching new-policy precision.'],['Weight 2','Critical service counts twice ordinary service','Moderate preference, still a weighted tradeoff.'],['Weight 10','Critical service counts ten times','Stronger preference, not strict lexicographic priority.'],['Critical-first','Maximize critical MW, retain its optimum within tolerance, then maximize total MW','Approximate lexicographic service allocation.']],[95,200,196])
    r.p('All policies use the same intact economic dispatch and the same physical constraints. The weights are normalized by their maximum without changing the weighted optimum. Critical-first normally uses a 1e-6 MW service floor tolerance. A numerical retry can switch off presolve and, only if necessary, relax the floor by a bounded recorded amount. Feasibility residual checks remain mandatory.')
    r.p('The main ramp sweep uses a group covering 25% of positive-demand bus count, rounded up, at ramp fractions 0.025,0.1,0.5. A nominal-ramp sweep uses 10%,25%,50% bus groups. There is one synthetic assignment per size; groups are not guaranteed nested. A 25% bus fraction need not be 25% of demand MW.')
    r.p('Case 14 evaluates all 380 ordered pairs for every policy. Cases 39 and 118 evaluate a shared union of default guided and flow attacks plus guided attacks under every policy, targeting either total loss or critical loss. This strengthens adversarial coverage but still examines only a small cohort of the 2,070 and 34,410 possible ordered pairs respectively.')
    r.section('13. Critical-service results and tradeoffs')
    rows=[]
    for name in ('14','39','118'):
        for policy in ('total-tight','weight-2','weight-10','critical-first'):
            a=cs[(cs.case==name)&(cs.fraction==.25)&(cs.ramp==.1)&(cs.policy==policy)].iloc[0]
            rows.append([name,policy,pct(a.critical_retained_fraction),num(a.shed_mw)])
    r.table(['Case','Policy','Mean worst critical retained','Mean worst total shed MW'],rows,[40,115,180,156])
    r.p('This table uses the matched-precision baseline. For each seed, critical retained is the minimum over the shared cohort, while total shed is the maximum; these may use different attacks. Larger cases are worst-found observations, not service guarantees. Reweighting cannot restore disconnected service. The original baseline is retained in the CSV and sensitivity plot.')
    r.table(['Policy vs total-tight','Paired rows','Critical improves','Critical worsens','Extra total loss'],[[a['policy'],a['pairs'],a['critical_improves'],a['critical_worsens'],a['extra_total_shed']] for a in pc if a['policy']!='total'],[140,70,93,93,95])
    r.p('Counts use a 0.001 MW reporting threshold. They describe repeated deterministic sequence/configuration pairs and do not estimate independent event probabilities. A policy can improve critical service by moving losses to ordinary demand. Myopic weighted or critical-first operation can also make a decision that harms critical service after a later cut.')
    r.h('Deliberately selected positive and adverse examples')
    for label,key in [('Largest critical-first gain','largest_gain'),('Largest critical-first harm','largest_harm')]:
        a=examples[key]
        r.p(f'{label}: case {a["case"]}, demand seed {int(a["seed"])}, group bus fraction {a["fraction"]}, ramp {a["ramp"]}, sequence {a["sequence"]}. Critical-service gain against total-tight is {num(a["critical_gain_mw"])} MW, with {num(a["extra_total_shed_mw"])} MW extra total loss. The example was selected after evaluation and is not representative.')
    r.section('14. Sensitivity, correctness and evidence limits')
    r.plot('priority.png',205)
    r.p('This plot retains the original total-service baseline alongside the new priorities. Use priority_precision_summary.csv for the matched-precision numerical control. Ramp changes alter available flexibility; group-size changes also alter membership. Neither should be interpreted as a causal study of one real service sector.')
    r.table(['Verification','Evidence'],[['Regression tests','16 extension tests passed, including cache order, protection equivalence, objective checks, time arithmetic and invalid inputs.'],['Default compatibility',f'{len(compatibility["probes"])} upstream replay-state probes, maximum difference {compatibility["max_state_difference_mw"]} MW.'],['Fresh defense replay','Cases 14/39, held-out seed 100, q=2: rebuild all eligible pairs and match saved maximum.'],['Cohort checks','Every priority policy and timing comparator has the same paired sequence set in each configuration.'],['Source and row coverage',f'{validation["oracle_tables"]} complete hashed outage tables, 45 priority configuration cells, explicit scenario and case identities.'],['Numerical feasibility',f'Max exported constraint residual {summary["max_residual"]:.3g} in native row units; max priority floor {summary["max_service_floor_tolerance_mw"]:.3g} MW.']],[130,361])
    r.p('A residual checks the returned solution against the implemented constraints. It cannot prove those constraints fully represent the real grid. Complete sequence enumeration does not resolve every alternative optimum of the operator. A finite-scenario exact defense optimum does not certify out-of-distribution performance. These are separate levels of evidence.')
    r.section('15. Original reproduction rerun')
    bench=OUT/'original_benchmark_status.json'
    if bench.exists():
        status=load('original_benchmark_status.json')
        r.p(status['description'])
        if (ROOT/'results'/'results.csv').exists():
            b=pd.read_csv(ROOT/'results'/'results.csv')
            rows=[]
            for (experiment,quality),g in b.groupby(['experiment','status']): rows.append([experiment,quality,len(g)])
            r.table(['Experiment','Reference error category','Rows'],rows,[260,150,81])
        if status.get('checker_output'): r.p('Original checker output: '+status['checker_output'])
    else:
        r.p('The original benchmark driver is separate from extension validation. Consult results/results.csv and the recorded original_benchmark_status.json for its execution and assertion status. Historical reference-match claims are not upgraded to current measurements by this report.')
    r.p('The released reference experiments use randomized load inputs whose exact original random state is not stored in this group repository. Replaying an author sequence separates part of the response-model/input difference from finding a different sequence. It still cannot recover an unknown input realization.')
    r.p('A failed threshold assertion is preserved as a reproduction limitation. It does not by itself invalidate a new within-model paired extension comparison, but it prevents claiming that every fresh experiment exactly reproduces the paper. The original driver also has response-skipping behavior, so its rows and check status should be interpreted with that caveat.')
    r.section('16. Conclusions and promising next steps')
    r.table(['Extension','Supported conclusion','What cannot be claimed'],[['Protection','Useful finite-model reduction on selected cases/budgets. Baseline ranking changes across held-out and stress conditions.','Universal superiority, robust investment optimality or real-grid protection.'],['Timing','Spacing and horizon change loss in a matched-decision discrete model. Final loss and the energy proxy answer different questions.','Continuous physical energy, calibrated equipment response or transient stability.'],['Priority service','Explicit priorities can preserve selected load while shifting or increasing other loss. Negative paired cases remain possible.','Guaranteed service in larger networks, a cost-free gain or actual hospital resilience.']],[87,214,190])
    r.h('Highest-value future work')
    r.p('1. Joint demand-and-ramp protection: train on the uncertainties that produced stress failures, then test on a separate scenario set. Include line-specific costs, imperfect protection and larger k. This directly addresses the observed generalization weakness.')
    r.p('2. Stronger critical-targeted attack search: use larger shortlists, full Greedy-IMPACT targeting critical loss, or an exact oracle where tractable. Test more synthetic group assignments or acquire defensible real service labels. A fixed sampled cohort is a useful comparison but a weak certificate.')
    r.p('3. Resolve response semantics deliberately: compare persistent shutdown with permitted restart, standardize dispatch tie rules and solver gap, and measure how these choices change extension conclusions. The paper describes no restart, while the group currently allows it.')
    r.p('4. Replace the energy proxy with explicit time trajectories: model continuous ramp paths, load restoration, storage state of charge and event times. Follow with AC feasibility, reactive power, frequency and relay validation.')
    r.p('5. Add limited operator lookahead under uncertain next events. This can test whether some adverse critical-first results come from myopic early decisions rather than an unavoidable physical service tradeoff.')
    r.section('17. File map and reproduction instructions')
    r.table(['Find this','File or directory'],[['Original physical model','grid_model.py'],['Original attacks and topology helpers','search_methods.py, network_metrics.py'],['New reusable algorithms','extensions.py'],['Experiment definitions and aggregation','run_extensions.py'],['Independent audits and precision control','audit_extensions.py'],['Unit tests','test_extensions.py'],['Detailed code comparison','IMPLEMENTATION_COMPARISON.md'],['Raw/aggregate evidence','results/extensions/*.csv and *.json'],['Complete pair tables','results/extensions/oracles/*.npz'],['Saved demonstrations','output/demonstration.html and results/extensions/demo_*.json'],['Speaking guide','PRESENTATION_GUIDE.md'],['Editable slide content','output/presentation/slide_content.json'],['Full report source','output/pdf/REPORT_SOURCE.md']],[175,316])
    r.code('pip install -r requirements-extensions.txt\npython -m pytest test_extensions.py -q\npython run_extensions.py --phase all --workers 2\npython audit_extensions.py --phase all --workers 2\npython build_deliverables.py')
    r.p('Only the optional comparison phase imports the neighboring implementation. With this checkout alone, run the protection, timing, priority and analyze phases separately. The extension algorithms and experiments are self-contained. The original benchmark commands remain python run_tests.py, python check_results.py and python make_plots.py.')
    r.p('Cached table keys include source fingerprint, case-file hash, scenario settings and SciPy version. Priority checkpoints include the experiment/source fingerprint. Changed physics, objectives or experiment protocols require fresh results, not manual edits to saved output. The report environment is recorded in summary.json.')
    r.section('18. Questions to expect in the presentation')
    qa=[('Are these the original paper authors\' implementation?','No. This is the group\'s independent SciPy reproduction. The authors released a separate Julia toolkit. Our new work extends the group code. [1,2]'),('Why can the same line failures give different losses?','Order changes the intermediate state. Model differences, solver precision and dispatch ties can also change the next ramp and service bounds.'),('Why does protection evaluation filter a table?','Protection only excludes certain attacks. It does not change how an eligible sequence behaves, so exact table filtering and fresh exhaustive replay are equivalent under that policy.'),('Why is a robust plan sometimes worse?','It optimizes a finite training scenario set and one nominal ramp. A different held-out or stress condition can favor another plan.'),('Why can strict critical priority fail later?','It optimizes current critical service, not all future sequences. Irreversible service decisions and generator changes can leave a worse later state.'),('Does 100% critical retained mean safety?','Only for the evaluated cohort, group and demand scenarios within this model. It does not cover unsearched attacks or omitted physical dynamics.'),('Is MWh a realistic blackout energy estimate?','It is a stated endpoint snapshot proxy. A realistic energy estimate needs a physical service trajectory inside every interval.'),('How much work is complete?','All three algorithms, fresh paired experiments, baseline/sensitivity evaluation, tests, result plots, saved demos and explanatory deliverables are included. Operational validation and the listed future work remain outside this project scope.')]
    for question,answer in qa:r.h(question);r.p(answer)
    r.section('19. References and provenance')
    refs=[('[1] Selected paper','Chio, A.; Bent, R.; Sundar, K.; Venkatasubramanian, N. SEQUIN: A Network Science and Physics-based Approach to Identify Sequential N-k Attacks in Electric Power Grids. ICCPS 2025. https://doi.org/10.1145/3716550.3722029. Supplied 12-page PDF inspected, especially Sections 3,4 and 6.'),('[2] Group source','https://github.com/AlankritGupta584/sequin-python-reproduction, commit e03e8495fb67af50f00c52daa75908e34960f151. The clean upstream source supplies default-compatibility probes.'),('[3] SciPy MILP documentation','https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html. MIP relative gap is a stopping tolerance, distinct from primal feasibility.'),('[4] HiGHS options documentation','https://ergo-code.github.io/HiGHS/dev/options/definitions/. The documented default mip_rel_gap is 0.0001; new priority policies and their total-tight control request 1e-8.'),('[5] Earlier local project','Neighboring sequin/ implementation and its source/results, also uploaded at https://github.com/Adventurist2/CS637. Used for source comparison and fixed-attack model probes, not as an extension simulation engine.'),('[6] Benchmark data','The six MATPOWER/PGLib files included by the group repository. Cases 14/39/118 drive the new extensions. Author reference CSVs remain historical comparison data.')]
    for title,text in refs:r.h(title);r.p(text)
    r.h('Measurement provenance')
    r.p('Extension source SHA-256: '+summary['source_sha256'],True)
    r.p('Runtime: '+json.dumps(summary['environment']),True)
    r.p('Complete measurements: results/extensions/. Default compatibility, oracle table metadata and validation.json provide audit trails. This report presents rounded values; CSV files retain full numerical precision.',True)
    r.build()


def demo():
    priority=load('demo_priority.json');timing=load('demo_timing.json');protection=load('demo_protection.json')
    examples=load('priority_examples.json');paired=[]
    for key,title in [('largest_gain','Selected largest gain'),('largest_harm','Selected largest harm')]:
        row=examples[key];case=case_obj(row['case'],int(row['seed']));critical=critical_group(case,row['fraction']);sequence=json.loads(row['sequence'])
        entry={'label':title,'case':row['case'],'seed':int(row['seed']),'fraction':row['fraction'],'ramp':row['ramp'],'sequence':sequence,'critical_bus_ids':json.loads(row['critical_bus_ids'])}
        for policy in ('total-tight','critical-first'):
            e=Evaluator(case,row['ramp'],policy='total' if policy=='total-tight' else policy,critical=critical)
            if policy=='total-tight':e.options['service_weights']=np.ones(len(case['bus']))
            entry[policy]=[{'round':j,**metrics(case,e.evaluate(sequence[:j]),critical)} for j in range(len(sequence)+1)]
        paired.append(entry)
    save_json(OUT/'demo_priority_paired.json',paired)
    payload=json.dumps({'priority':paired,'timing':timing,'protection':protection}).replace('</','<\\/')
    html='''<!doctype html><html><head><meta charset="utf-8"><title>SEQUIN group extension demonstrations</title><style>
body{font:17px/1.6 Arial,sans-serif;max-width:1100px;margin:40px auto;padding:0 25px;color:#183544;background:#f5f3ee}h1,h2{line-height:1.2}section{margin:50px 0}table{border-collapse:collapse;width:100%;background:white}th,td{border-bottom:1px solid #ccd8db;padding:10px;text-align:left}th{background:#dce8e8}select{font:inherit;padding:7px} .note{color:#586d75}pre{white-space:pre-wrap;background:#e7edeb;padding:16px}</style></head><body>
<h1>SEQUIN: three extensions on the group model</h1><p>These examples replay saved SciPy responses. Changing a selector displays a recorded experiment. No optimization runs in your browser.</p>
<section><h2>1. Protected lines and adaptive attacks</h2><select id="protect"></select><p id="pdesc"></p><div id="ptable"></div></section>
<section><h2>2. Response timing</h2><p class="note">Three redispatch decisions for both comparators. Energy is an endpoint response-then-hold snapshot proxy.</p><select id="timing"></select><p id="tdesc"></p><div id="ttable"></div></section>
<section><h2>3. Critical service and its cost</h2><p class="note">Selected largest-gain and largest-harm examples against the matched-precision total-service baseline. These extremes are not representative.</p><select id="critical"></select><p id="cdesc"></p><div id="ctable"></div></section>
<section><h2>Review the implementation</h2><p>Start with grid_model.py, then search_methods.py, extensions.py, run_extensions.py and audit_extensions.py. The project report and guide explain scope, failures and reproduction commands.</p></section>
<script>const D=PAYLOAD;
const f=x=>Number(x).toFixed(3);const tab=(headers,rows)=>'<table><thead><tr>'+headers.map(x=>'<th>'+x+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(x=>'<td>'+x+'</td>').join('')+'</tr>').join('')+'</tbody></table>';
const p=document.getElementById('protect');D.protection.forEach((x,i)=>p.add(new Option('Case '+x.case,i)));function showP(){const x=D.protection[p.value];document.getElementById('pdesc').textContent='Demand seed '+x.seed+'. Protected line IDs: '+x.protected.join(', ')+'. Adaptive attack: '+x.sequence.join(', ')+'.';document.getElementById('ptable').innerHTML=tab(['Round','Failed lines','Total shed MW'],x.states.map(s=>[s.round,s.failed.join(', '),f(s.shed_mw)]));}p.onchange=showP;showP();
const t=document.getElementById('timing');D.timing.forEach((x,i)=>t.add(new Option(x.pattern+' / '+(x.simultaneous?'simultaneous':'sequential'),i)));function showT(){const x=D.timing[t.value];document.getElementById('tdesc').textContent='Attack '+x.sequence.join(', ')+'. Final loss '+f(x.final_shed_mw)+' MW. Snapshot energy proxy '+f(x.snapshot_unserved_energy_mwh)+' MWh.';document.getElementById('ttable').innerHTML=tab(['Window','Minutes','New failures','Shed MW'],x.windows.map(w=>[w.window,w.duration_minutes,w.new_failures.join(', '),f(w.shed_mw)]));}t.onchange=showT;showT();
const c=document.getElementById('critical');D.priority.forEach((x,i)=>c.add(new Option(x.label,i)));function showC(){const x=D.priority[c.value],a=x['total-tight'],b=x['critical-first'];document.getElementById('cdesc').textContent='Case '+x.case+', seed '+x.seed+', group fraction '+x.fraction+', ramp '+x.ramp+', attack '+x.sequence.join(', ')+'. Critical bus IDs: '+x.critical_bus_ids.join(', ')+'.';document.getElementById('ctable').innerHTML=tab(['Round','Baseline critical shed MW','Priority critical shed MW','Baseline total shed MW','Priority total shed MW'],a.map((s,i)=>[i,f(s.critical_shed_mw),f(b[i].critical_shed_mw),f(s.shed_mw),f(b[i].shed_mw)]));}c.onchange=showC;showC();
</script></body></html>'''.replace('PAYLOAD',payload)
    DEST.mkdir(exist_ok=True);(DEST/'demonstration.html').write_text(html,encoding='utf-8')


def presentation_content():
    # The JSON is consumed by the editable presentation builder.
    ps=csv('protection_summary.csv');ts=csv('timing_summary.csv');cs=csv('priority_precision_summary.csv');s=load('summary.json');v=load('validation.json');ex=load('priority_examples.json')
    slides=[]
    source='Source: group-sequin/results/extensions/; '+s['source_sha256']+'. Group upstream e03e8495fb67af50f00c52daa75908e34960f151.'
    def add(title,body=None,table=None,charts=None,note='',footer=''):
        slides.append({'title':title,'body':body,'table':table,'charts':charts,'notes':note+'\n'+source,'footer':footer})
    def chart(case,frame='protection'):
        if frame=='protection':
            policies=[('robust-sequential','Scenario design',TEAL),('initial-flow','Initial flow',ORANGE),('single-scenario','Single scenario',PURPLE),('simultaneous-design','Simultaneous design','#8A8D91')]
            return {'categories':['0','1','2','3'],'series':[{'name':label,'values':(ps[(ps.case==case)&(ps.policy_group==p)].sort_values('budget').shed_fraction*100).tolist(),'color':color} for p,label,color in policies],'x':'Protected lines q','y':'Mean test worst shed (%)'}
    add('The paper: why failure order matters',body=['One line fails. The operator adjusts generation and may shed demand.','The next failure acts on that changed state.','SEQUIN searches for damaging orders using network clues and constrained responses.'],note='Use the road-network analogy, then explain that power flows obey physical equations and cannot be arbitrarily routed. The defender is myopic. Cite Chio et al., ICCPS 2025, Sections 3-4, DOI 10.1145/3716550.3722029.')
    add('The defender and its carried state',table=[['Quantity','Model rule'],['Line flow','DC relation, rating and angle-difference limits'],['Generation','Capacity and previous output +/- alpha Pmax, or shutdown'],['Served demand','Cannot exceed service retained in the previous round'],['Network','Failed lines remain out; each island has a reference angle']],note='Power is in MW in this code. The original loss output divides by baseMVA. A generator can switch off completely. The group code permits later restart because it does not carry z. The paper describes no restart in Eq. 2f. No AC voltage, frequency, relay or transient simulation.')
    add('Group implementation: code reading order',table=[['File','Role'],['grid_model.py','Parse cases, initial LP, response MILP'],['search_methods.py','Exact, greedy and top-flow guided attacks'],['network_metrics.py','Flow margins and structural heuristics'],['extensions.py','Protection, timing, priority and prefix cache'],['run_extensions.py','Fresh studies, summaries and trace examples'],['audit_extensions.py','Independent replays and precision controls']],note='The first three files already existed upstream. New responses still use this repository\'s grid_model.defend. The earlier neighboring sequin package is only imported by the optional comparison phase.')
    add('Why the two implementations differ',table=[['Aspect','Group model','Earlier project'],['Power units','MW','Per-unit internally'],['Generator shutdown','Restart permitted next round','Persistent shutdown'],['Response ties','Single objective','Economic tie-break'],['Solver precision','Default MIP gap','Explicit 1e-8'],['Attack guidance','Top-flow shortlist','Multiple network properties']],note='There are additional angle-box, negative-injection and RNG differences in the report. No single factor is established as the cause of every mismatch. The six supplied cases have zero quadratic costs and active shunts, so those generic feature differences do not explain these measurements.')
    add('The same attack can produce different loss',charts=[{'type':'bar','categories':['Case 14 (3,1)','Case 118 (104,97)'],'series':[{'name':'Group','values':[439.97,531.398],'color':TEAL},{'name':'Earlier project','values':[462.97,1192.347],'color':ORANGE}],'y':'Final shed MW'}],footer='Selected fixed attacks on unperturbed identical inputs',note='This is a model-comparison example, not a quality ranking. Different dispatch choices, shutdown/restart semantics and numerical settings can alter later ramp states. Default-compatibility replay of the new defender against untouched upstream source gives exactly matching generation and service on all 26 probes.')
    add('Original reproduction rerun',body=['The original driver completed 311 measured rows and seven plots.','Its unchanged checker fails because case 162, k=8 is missing.','Fresh replay confirms the eighth response MILP is infeasible.','Selected reference matches coexist with larger discrepancies.'],note='The failed prefix is [83,5,19,228,196,177,212,219]. The original driver skipped the unsuccessful response. Case-14 guided results match selected reference budgets. Case-39 guided k=6 differs by about -2.075%, slightly beyond its 2% checker threshold. Full benchmark rows and the recorded solver status remain in results/. This does not establish exact reproduction of every paper result.')
    add('Critique and the three extensions',table=[['Gap','Extension','Practical question'],['No investment selection','Scenario-aware protection','Which limited set of lines should we protect?'],['Fixed response epochs','Variable response windows','What changes when failures arrive closer together?'],['All MW valued equally','Critical-service objectives','Which services should retain power first?']],note='The paper explicitly proposes ruggedization and variable epochs as future work in Section 6. Priority service is a realistic course-project extension with synthetic labels. Do not claim these general research ideas are invented here.')
    add('Evaluation design',table=[['Study','Cases','Comparison scope'],['Protection','14, 39','All ordered pairs, train/test split, q=0-3'],['Timing','14, 39, 118','Common triple-order cohort, three horizons'],['Priority','14, 39, 118','All pairs on 14, shared targeted cohort on 39/118']],footer='Demand scenarios are the experimental unit',note=f'Protection has {s["rows"]["protection"]} rows, timing {s["rows"]["timing"]}, and priority {s["rows"]["priority"]}. Row counts include deterministic repeats and policy comparisons. Protection design seeds 0/1/2 and held-out seeds 100-104 are separate. Other studies use demand seeds 0/1/2.')
    add('Extension 1: adaptive line protection',body=['Build complete k=2 ordered-outage tables for each design demand.','Add the protected line that minimizes worst design-scenario loss.','After choosing q lines, let the attack adapt over every eligible pair.','Compare random, flow, betweenness, single-scenario and simultaneous designs.'],note='Protection changes outage eligibility only. It leaves physical response on an eligible sequence unchanged, so filtering complete tables is valid. Exact outer protection enumeration for q<=2 is a separate small-instance oracle. Greedy has no general global guarantee.')
    add('Protection on case 14',charts=[chart('14')],note='Lower loss is better. Each point averages held-out scenario worst losses, not a fixed common attack. At q=2 the scenario design helps substantially. At q=1 it fails to improve held-out worst loss, while the single-scenario plan does improve it. This is an important generalization caveat.')
    add('Protection on case 39',charts=[chart('39')],note='Initial-flow protection slightly outperforms the robust design on held-out seeds at q=2. The scenario design improves more at q=3. Training-objective optimality does not establish the best unseen-scenario performance. Include both outcomes in the presentation.')
    add('Protection under shifted conditions',body=[f'Nominal robust design loses to flow in {s["stress_robust_worse_than_flow"]} of {s["stress_comparisons"]} feasible stress cells.',f'Worst excess loss: {num(s["stress_worst_excess_pp"])} percentage points.',f'{s["rows"]["stress_initial_infeasible"]} policy rows have an infeasible intact starting scenario.','Next step: train protection across demand and ramp uncertainty.'],note='A cell is a case, demand seed, ramp, demand spread and budget combination. Unperturbed seeds duplicate the same demand. Infeasible starting cases have no fabricated attack loss. The line plan remains frozen during stress evaluation.')
    add('Extension 2: matched response windows',table=[['Pattern','Minutes at H=15','Sequential failures'],['Even','5, 5, 5','One new failure per window'],['Early cluster','1, 1, 13','Short early responses'],['Late cluster','13, 1, 1','Short final responses']],footer='Both comparators receive three redispatch decisions',note='The simultaneous policy loses the whole set in the first window, then can respond twice more. Each window uses alpha Pmax times duration/5. Horizons are 7.5/15/30 minutes. Rates are derived assumptions, not equipment measurements.')
    timingcharts=[]
    for metric,label in [('final_shed_fraction','Final shed (%)'),('snapshot_energy_fraction','Snapshot energy proxy (%)')]:
        a=ts[(ts.case=='118')&(ts.horizon_minutes==15)]
        timingcharts.append({'type':'bar','categories':['Even','Early','Late'],'series':[{'name':label2,'values':[100*float(a[(a.pattern==p)&(a.simultaneous==sim)].iloc[0][metric]) for p in ('even','early','late')],'color':col} for sim,label2,col in [(False,'Sequential',TEAL),(True,'Simultaneous',ORANGE)]],'y':label})
    add('Timing: final MW and time weighting differ',charts=timingcharts,footer='Case 118, 15 minutes; mean per-seed cohort maxima',note='The final-loss maximum and proxy-energy maximum may use different sequences. The snapshot proxy sums endpoint loss times duration, normalized by initial demand times horizon. It is not physical integration of continuous ramping. A worse final loss can still have a smaller proxy when it appears late.')
    add('The energy measure and its limit',body=['Snapshot proxy = sum(endpoint shed MW x window minutes / 60).','The solver uses each window’s ramp allowance, then holds the endpoint loss for accounting.','Continuous generation and service paths inside each window remain unmodeled.'],note='Say response-then-hold snapshot proxy every time you interpret MWh. Do not call it a validated blackout-energy forecast. Restore-load dynamics, continuous ramps and transient feasibility are future work.')
    add('Extension 3: critical-service response',table=[['Policy','What the operator maximizes'],['Total-tight','Total MW, using matched 1e-8 MIP precision'],['Weight 2','Critical MW counts twice other MW'],['Weight 10','Critical MW counts ten times'],['Critical-first','Critical MW first, then total MW within a recorded floor tolerance']],footer='Synthetic bus groups; identical initial dispatch and attack cohort',note='Group seed 17 selects positive-demand buses. Fractions are bus counts, not MW fractions, and assignments need not be nested. One group assignment per size is a limitation. The original total-service policy is retained as an extra comparison.')
    nominal=[]
    for policy,label,col in [('total-tight','Total-tight','#8A8D91'),('weight-2','Weight 2',TEAL),('weight-10','Weight 10',PURPLE),('critical-first','Critical-first',ORANGE)]:
        nominal.append({'name':label,'values':[100*float(cs[(cs.case==n)&(cs.fraction==.25)&(cs.ramp==.1)&(cs.policy==policy)].iloc[0].critical_retained_fraction) for n in ('14','39','118')],'color':col})
    add('Critical service at the nominal setting',charts=[{'type':'bar','categories':['Case 14','Case 39','Case 118'],'series':nominal,'y':'Mean worst critical retained (%)'}],footer='25% of positive-demand buses; ramp 0.1',note='Higher retention is better. Each policy is evaluated on exactly the same sequence set within a scenario. Case 14 is exhaustive. Cases 39/118 are sampled worst-found results, including critical-loss-targeted attacks. Rounded 100% retention is not a guarantee against unsearched attacks.')
    a=ex['largest_gain'];b=ex['largest_harm']
    add('Critical gains have costs and adverse cases',table=[['Selected case','Critical gain MW','Extra total loss MW'],[f'Largest gain: case {a["case"]}',num(a['critical_gain_mw']),num(a['extra_total_shed_mw'])],[f'Largest harm: case {b["case"]}',num(b['critical_gain_mw']),num(b['extra_total_shed_mw'])]],body=['Comparisons use the total-tight baseline.','These examples are deliberately selected extremes.'],note='Give the full scenario and attack from priority_examples.json if asked. A negative gain means critical-first harmed later critical service. Myopic optimization maximizes service now, not across all future outages. Extra total loss can reflect a deliberate sacrifice of ordinary load.')
    counts=load('priority_precision_comparison.json')
    add('Priority outcomes across paired sequences',table=[['Policy','Improves critical','Worsens critical','Extra total loss']]+[[x['policy'],str(x['critical_improves']),str(x['critical_worsens']),str(x['extra_total_shed'])] for x in counts if x['policy']!='total'],footer='Counts at 0.001 MW threshold; repeated deterministic pairs',note='Do not interpret these counts as independent event probabilities. They include repeated configurations and demand scenarios. The matched-precision total-service control separates the policy objective from the default solver gap.')
    add('Correctness and claim boundaries',body=[f'16 regression tests pass; {len(load("default_compatibility.json")["probes"])} upstream state probes match exactly.','Fresh exhaustive post-protection replays match saved table maxima.','All policies share the same paired attacks in each configuration.','Small cases are exhaustive. Larger critical/timing studies report worst found.'],note=f'The exported residual maximum is {s["max_residual"]:.3g} native row units. Residual checks validate the implemented mathematical constraints, not real-grid adequacy. Exact tables do not handle all dispatch ties or remove numerical MIP tolerances.')
    add('What the results establish',table=[['Extension','Conclusion'],['Protection','Useful gains, with held-out and stress failures against baselines'],['Timing','Spacing changes final loss and the snapshot proxy'],['Critical service','Better selected service can increase other loss; adverse later cases remain']],note='Report improvement, inconclusion and failure honestly. None of these studies establishes broad real-world safety. The work completes the bounded second-part course-project scope.')
    add('Future work motivated by the failures',body=['Train protection jointly across demand and response-speed uncertainty.','Strengthen critical-loss attack search and vary priority-group assignments.','Standardize shutdown, dispatch ties and numerical precision.','Model continuous ramps, restoration and storage, then test AC feasibility.'],note='Prioritize joint robust protection because stress failures were measured, and targeted critical search because the larger cohorts are small. Operator lookahead can test whether myopic choices explain adverse priority cases.')
    add('Demonstration and review route',body=['Open output/demonstration.html for saved protection, timing and priority traces.','Read grid_model.py, then extensions.py and run_extensions.py.','Use audit_extensions.py to check paired cohorts and fresh exact replays.','Full derivations, results and limitations are in the separate PDF report.'],note='If presenting live, run the saved demo first. Optimization is offline, so the browser only selects precomputed traces. Commands and artifact locations are in EXTENSIONS_README.md and PRESENTATION_GUIDE.md.')
    (DEST/'presentation').mkdir(parents=True,exist_ok=True);save_json(DEST/'presentation'/'slide_content.json',slides)
    guide=['# Presentation speaking guide','', 'The presentation has one cover plus '+str(len(slides))+' content slides. All measurements use the group model. The PDF is a separate full report.','']
    for i,x in enumerate(slides,2):
        guide += [f'## Slide {i}: {x["title"]}',x['notes'],'']
    guide += ['## Short project explanation','The paper finds damaging orders of line failures. Our group reproduces the response model and search. We then ask which lines to protect, how response time changes loss, and how to prioritize selected services. We rerun the measurements on the group model, report useful gains and failures, and preserve the scope limits.','', '## Before presenting','Use the exact same dataset and source version as the saved report. Treat large-grid cohort results as worst found. Do not equate a time-weighted snapshot proxy with continuous physical energy. Do not treat repeated deterministic rows as independent samples.']
    (ROOT/'PRESENTATION_GUIDE.md').write_text('\n'.join(guide),encoding='utf-8')


if __name__=='__main__':
    report();demo();presentation_content();print(PDF)

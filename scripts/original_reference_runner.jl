# Execute the authors' extracted functions without rewriting their algorithms.
# The plan is JSON; source files remain untouched. All outputs are new files.
using Random
using Dates

const ROOT = normpath(joinpath(@__DIR__, ".."))
const SOURCE = joinpath(ROOT, "reproduction", "docker_reference")

function project_reference(path)
    relative = try
        relpath(abspath(path), ROOT)
    catch
        return basename(path)
    end
    parts = splitpath(relative)
    if isabspath(relative) || (!isempty(parts) && first(parts) == "..")
        return basename(path)
    end
    return replace(relative, '\\'=>'/')
end

module OriginalSEQUIN
using PowerModels
using JuMP
using Gurobi
using PrettyTables
using Logging
using Combinatorics
const SRC = joinpath(@__DIR__, "..", "reproduction", "docker_reference", "src")
for path in ["utils/cliparser.jl", "utils/types.jl", "utils/utils.jl", "utils/ioutils.jl",
             "utils/datautils.jl", "utils/optimizationutils.jl", "outer/traditional.jl",
             "outer/permutation.jl", "outer/enumeration.jl", "outer/greedy-criticality.jl",
             "outer/greedy-flow.jl", "outer/greedy-impact.jl", "outer/ours.jl",
             "inner/pm_model.jl", "inner/dc-ls-traditional.jl", "inner/dc-ls-permutation.jl",
             "outer/run.jl", "inner/dc-ls.jl", "network_properties/network-properties.jl"]
    include(joinpath(SRC, path))
end
# The original top-level environment is unused by its functions. Defer license
# acquisition to the actual solve so a missing license is a structured job error.
const GRB_ENV = nothing
const DEBUG = false
PowerModels.silence()
end

const O = OriginalSEQUIN
const JSON = O.PowerModels.JSON
const CASES = Dict("14"=>"pglib_opf_case14_ieee__api.m", "39"=>"pglib_opf_case39_epri__api.m",
    "60"=>"pglib_opf_case60_c.m", "118"=>"pglib_opf_case118_ieee__api.m",
    "162"=>"pglib_opf_case162_ieee_dtc.m", "240"=>"pglib_opf_case240_pserc.m")

function writejson(path, value)
    mkpath(dirname(path))
    temporary=path*".tmp"
    open(temporary, "w") do stream
        JSON.print(stream, value, 2)
    end
    mv(temporary,path;force=true)
end

function args_for(job, output)
    cli = O.parse_commandline() # ARGS is emptied after reading the plan filename.
    cli["case"] = CASES[string(job["case"])]
    cli["data_path"] = replace(joinpath(SOURCE, "data"), '\\'=>'/') * "/"
    cli["output_path"] = replace(output, '\\'=>'/') * "/"
    cli["use_separate_budgets"] = true
    cli["budget"] = cli["line_budget"] = Int(get(job,"k",2))
    cli["generator_budget"] = 0
    cli["iterline_budget"] = 1
    cli["generator_ramping_bounds"] = Float64(get(job,"ramp",0.1))
    cli["do_perturb_loads"] = Bool(get(job,"perturb",true))
    cli["timeout"] = Int(get(job,"solver_timeout",120))
    cli["optimality_gap"] = 1.0 # helper divides by 100: paper's stated 1% MIP gap
    cli["inner_solver"] = "gurobi"
    cli["failed"] = ""
    cli["exp_repeat"] = 1
    return cli
end

function export_scenario(data, ref)
    return Dict("base_mva"=>data["baseMVA"], "total_load_pu"=>data["total_load"],
        "buses"=>[Dict("id"=>i) for i in sort(collect(keys(ref[:bus])))],
        "loads"=>[Dict("id"=>i, "bus"=>v["load_bus"], "pd"=>v["pd"]) for (i,v) in sort(collect(ref[:load]);by=first)],
        "generators"=>[Dict("id"=>i, "bus"=>v["gen_bus"], "pg"=>v["pg"], "pmin"=>v["pmin"], "pmax"=>v["pmax"])
                       for (i,v) in sort(collect(ref[:gen]);by=first)],
        "branches"=>[Dict("id"=>i, "from"=>v["f_bus"], "to"=>v["t_bus"], "r"=>v["br_r"], "x"=>v["br_x"],
                          "tap"=>v["tap"], "shift"=>v["shift"], "flow"=>v["pf"], "rating"=>v["rate_a"])
                     for (i,v) in sort(collect(ref[:branch]);by=first)])
end

function compute(job, output)
    Random.seed!(Int(get(job,"seed",0)))
    cli = args_for(job, output)
    file = joinpath(SOURCE,"data","matpower",cli["case"])
    data, ref = O.init_models_data_ref(file; do_perturb_loads=cli["do_perturb_loads"])
    method = string(get(job,"method","probe"))
    scenario = export_scenario(data,ref)
    if method == "probe"
        setpoints=Dict(i=>g["pg"] for (i,g) in ref[:gen])
        line = minimum(keys(ref[:branch]))
        cut=O.get_traditional_inner_solution(data,ref,[],[line],setpoints;
                        percent_change=cli["generator_ramping_bounds"],solver="gurobi")
        return Dict("shed_pu"=>cut.load_shed,"line"=>line,"scenario"=>scenario)
    end
    if method == "trace"
        loads=Dict(i=>v["pd"] for (i,v) in ref[:load])
        pg=Dict(i=>v["pg"] for (i,v) in ref[:gen])
        state=O.IterData(loads,pg)
        trace=[]
        for line in Int.(job["sequence"])
            previous=Dict("generation"=>copy(state.prev_gen_setpoints),"loads"=>copy(state.prev_loads))
            push!(state.lines,line)
            cut=O.get_permutation_inner_solution(data,ref,[],state.lines,state;
                        percent_change=cli["generator_ramping_bounds"],solver="gurobi")
            push!(trace,Dict("previous"=>previous,"failed"=>copy(state.lines), "shed_pu"=>cut.load_shed,
                 "generation"=>cut.pg,"loads"=>cut.loads,"flow"=>cut.p))
            state.prev_gen_setpoints=cut.pg
            state.prev_loads=cut.loads
        end
        return Dict("scenario"=>scenario,"trace"=>trace)
    end
    start=time()
    if method == "std"
        result=O.solve_traditional(cli,data,ref)
        best=result.solution
        return Dict("shed_pu"=>best.load_shed,"sequence"=>best.lines,"seconds"=>time()-start,
                    "scenario"=>scenario,"relative_gap"=>result.optimality_gap)
    end
    result = if method == "sequin"
        O.solve_approach(cli,data,ref)
    elseif method == "flow"
        O.solve_greedy_flow(cli,data,ref)
    elseif method == "shed"
        O.solve_greedy_impact(cli,data,ref)
    elseif method == "crit"
        O.solve_greedy_criticality(cli,data,ref)
    elseif method == "enum"
        O.solve_enumeration(cli,data,ref)
    elseif method == "perm"
        O.solve_permutation(cli,data,ref)
    else
        error("Unknown original method $method")
    end
    solutions=collect(values(result.solution.solutions))
    all(isfinite(s.load_shed) for s in solutions) || error("Original search returned nonfinite sequence values")
    if method == "enum"
        n=length(ref[:branch]);k=Int(job["k"])
        expected=prod(big(n-i) for i in 0:k-1)
        length(solutions)==expected || error("Incomplete original enumeration: $(length(solutions))/$expected")
    end
    best=solutions[argmax([s.load_shed for s in solutions])]
    return Dict("shed_pu"=>best.load_shed,"sequence"=>best.lines,"seconds"=>time()-start,
                "scenario"=>scenario,"sequences"=>[Dict("sequence"=>s.lines,"shed_pu"=>s.load_shed) for s in solutions])
end

function main()
    planfile=abspath(only(ARGS)); empty!(ARGS)
    plan=JSON.parsefile(planfile)
    output=abspath(plan["output"]);mkpath(output)
    results=[]
    for (index,job) in enumerate(plan["jobs"])
        name=get(job,"id",string(index))
        path=joinpath(output,"jobs",name*".json")
        if isfile(path) && get(plan,"resume",true)
            cached=JSON.parsefile(path)
            if cached["status"] == "ok" || get(plan,"resume_errors",false)
                push!(results,cached);continue
            end
        end
        row=Dict{String,Any}("id"=>name,"job"=>job,"julia_version"=>string(VERSION),
            "gurobi_version"=>string(O.Gurobi.GRB_VERSION_MAJOR,".",O.Gurobi.GRB_VERSION_MINOR,".",O.Gurobi.GRB_VERSION_TECHNICAL),
            "started_utc"=>string(now(UTC)))
        started=time()
        try
            row["result"]=compute(job,output)
            row["status"]="ok"
        catch err
            row["status"]="error"
            row["error"]=sprint(showerror,err)
            showerror(stderr,err,catch_backtrace());println(stderr)
        end
        row["wall_seconds"]=time()-started
        writejson(path,row);push!(results,row)
        writejson(joinpath(output,"results.json"),Dict("source"=>"original extracted Julia functions; no algorithm modifications",
            "plan"=>project_reference(planfile),"results"=>results))
        println("REFERENCE_PROGRESS ",name," ",row["status"]);flush(stdout)
    end
    writejson(joinpath(output,"results.json"),Dict("source"=>"original extracted Julia functions; no algorithm modifications",
        "plan"=>project_reference(planfile),"results"=>results))
    return all(row["status"]=="ok" for row in results) ? 0 : 1
end

if abspath(PROGRAM_FILE) == abspath(@__FILE__)
    exit(main())
end

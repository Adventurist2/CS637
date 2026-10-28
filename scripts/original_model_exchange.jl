# Build exact original PowerModels/SEQUIN models in Julia and export MPS.
# Solve only through the supported gurobipy interface; enforce its normal license.
include(joinpath(@__DIR__, "original_reference_runner.jl"))

function exchange_solve(pm, folder, tag)
    mkpath(folder)
    for (i,v) in enumerate(O.JuMP.all_variables(pm.model))
        O.JuMP.set_name(v,"v"*string(i))
    end
    mps=joinpath(folder,tag*".mps")
    solution=joinpath(folder,tag*"_solution.json")
    O.JuMP.write_to_file(pm.model,mps)
    python=joinpath(ROOT,".venv","Scripts","python.exe")
    command=`$python $(joinpath(@__DIR__,"solve_original_mps.py")) $mps $solution`
    run(ignorestatus(command))
    result=JSON.parsefile(solution)
    result["status"] == "ok" || error(result["error"])
    return result
end

function solved_value(solution, expression)
    if expression isa O.JuMP.VariableRef
        return solution["values"][O.JuMP.name(expression)]
    end
    return O.JuMP.value(v->solution["values"][O.JuMP.name(v)],expression)
end

function exchange_initialize(file, job, folder)
    perturb=Bool(get(job,"perturb",true))
    for attempt in 1:(perturb ? 11 : 1)
        data=O.PowerModels.parse_file(file;validate=false)
        O.PowerModels.make_per_unit!(data)
        if perturb && attempt<=10
            O.perturb_loads!(data;by=0.05)
        end
        O.add_total_load_info!(data)
        O.modify_generation_limits!(data)
        pm=O.instantiate_model(data,O.DCPPowerModel,O.build_opf)
        try
            solution=exchange_solve(pm,folder,"initial")
            for id in O.PowerModels.ids(pm,:gen)
                variable=O.PowerModels.var(pm,:pg)[id]
                data["gen"][string(id)]["pg"]=solved_value(solution,variable)
            end
            for arc in O.PowerModels.ref(pm,:arcs_from)
                variable=O.PowerModels.var(pm,:p)[arc]
                id,from,to=arc
                if data["branch"][string(id)]["f_bus"] == from
                    data["branch"][string(id)]["pf"]=solved_value(solution,variable)
                end
            end
            ref=O.PowerModels.build_ref(data)[:it][:pm][:nw][0]
            return data,ref,solution
        catch err
            text=sprint(showerror,err)
            # Size/license errors do not improve on resampling; never route around them.
            if !perturb || attempt==11 || occursin("license",lowercase(text)) || occursin("too large",lowercase(text))
                rethrow(err)
            end
        end
    end
end

function exchange_compute(job,output)
    Random.seed!(Int(get(job,"seed",0)))
    name=string(job["id"])
    folder=joinpath(output,"models",name)
    file=joinpath(SOURCE,"data","matpower",CASES[string(job["case"])])
    data,ref,initial=exchange_initialize(file,job,folder)
    scenario=export_scenario(data,ref)
    ramp=Float64(get(job,"ramp",0.1))
    loads=Dict(i=>v["pd"] for (i,v) in ref[:load])
    pg=Dict(i=>v["pg"] for (i,v) in ref[:gen])
    failed=Int[]
    trace=[]
    sequence=Int.(get(job,"sequence",[minimum(keys(ref[:branch]))]))
    for (round,line) in enumerate(sequence)
        previous=Dict("generation"=>copy(pg),"loads"=>copy(loads))
        push!(failed,line)
        # These are the authors' own preprocessing/model-builder functions.
        case=O.interdict_components(data,[],failed;make_deepcopy=true)
        O.modify_loads!(case,loads)
        pm=O.instantiate_model(deepcopy(case),O.DCPPowerModel,
            pm->O.my_build_mld(pm,pg;percent_change=ramp))
        solved=exchange_solve(pm,folder,"round"*string(round))
        loads=Dict(i=>O.PowerModels.ref(pm,:load)[i]["pd"]*solved_value(solved,O.PowerModels.var(pm,:z_demand)[i])
                   for i in O.PowerModels.ids(pm,:load))
        pg=Dict(i=>solved_value(solved,O.PowerModels.var(pm,:pg)[i]) for i in O.PowerModels.ids(pm,:gen))
        flows=Dict{Int,Float64}()
        for arc in O.PowerModels.ref(pm,:arcs_from)
            v=O.PowerModels.var(pm,:p)[arc]
            flows[arc[1]]=max(get(flows,arc[1],0.0),abs(solved_value(solved,v)))
        end
        shed=data["total_load"]-sum(values(loads);init=0.0)
        push!(trace,Dict("previous"=>previous,"failed"=>copy(failed),"shed_pu"=>shed,
            "generation"=>pg,"loads"=>loads,"flow"=>flows,
            "objective"=>solved["objective"],"objective_bound"=>solved["objective_bound"],"mip_gap"=>solved["mip_gap"],
            "variables"=>solved["variables"],"constraints"=>solved["constraints"]))
    end
    return Dict("scenario"=>scenario,"trace"=>trace,"initial_variables"=>initial["variables"],
        "initial_constraints"=>initial["constraints"],"solver_interface"=>"gurobipy 12.0.3 via exact original Julia-exported MPS")
end

function exchange_main()
    planfile=abspath(only(ARGS));empty!(ARGS)
    plan=JSON.parsefile(planfile)
    output=abspath(plan["output"])
    results=[]
    for job in plan["jobs"]
        path=joinpath(output,"jobs",job["id"]*".json")
        if isfile(path) && get(plan,"resume",true)
            previous=JSON.parsefile(path)
            if previous["status"]=="ok"
                push!(results,previous);continue
            end
        end
        row=Dict{String,Any}("id"=>job["id"],"job"=>job,"started_utc"=>string(now(UTC)),
            "backend"=>"original Julia model construction + gurobipy model solve")
        started=time()
        try
            row["result"]=exchange_compute(job,output)
            row["status"]="ok"
        catch err
            row["status"]="error";row["error"]=sprint(showerror,err)
            showerror(stderr,err,catch_backtrace());println(stderr)
        end
        row["wall_seconds"]=time()-started
        writejson(path,row);push!(results,row)
        writejson(joinpath(output,"results.json"),Dict("fresh_optimization"=>true,
             "scope"=>"Original model construction; supported Python solver interface; not native Julia search program",
             "results"=>results))
        println("EXCHANGE_PROGRESS ",job["id"]," ",row["status"]);flush(stdout)
    end
    writejson(joinpath(output,"results.json"),Dict("fresh_optimization"=>true,
        "scope"=>"Original model construction; supported Python solver interface; not native Julia search program",
        "results"=>results))
    return all(row["status"]=="ok" for row in results) ? 0 : 1
end

exit(exchange_main())

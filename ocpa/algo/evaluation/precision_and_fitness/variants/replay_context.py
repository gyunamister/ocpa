import gc
from itertools import combinations
import copy
import pandas as pd
from collections import Counter
import time
import itertools
from itertools import chain
from itertools import product

def enabled(model,state,transition):
        enabled = True
        for a in transition.in_arcs:
            if a.source not in state[0].keys():
                enabled = False
            elif len(list(state[0][a.source].elements())) < 1:
                enabled = False
        return enabled
    
def context_to_string_verbose(context):
    cstr = ""
    for key in context.keys():
        cstr+=key
        for c in context[key].most_common():
            cstr+=",".join(c[0])
            cstr+=str(c[1])
    return cstr

def context_to_string(context):
    return hash(tuple([hash(tuple(sorted(context[cc].items()))) for cc in context.keys()]))
    cstr = ""
    for key in context.keys():
        cstr+=key
        for c in context[key].most_common():
            cstr+=",".join(c[0])
            cstr+=str(c[1])
    return cstr

def patched_most_common(self):
    return sorted(self.items(), key=lambda x: (-x[1],x[0]))


def row_to_binding(row,object_types):
    return (row["event_activity"],{ot:row[ot] for ot in object_types},row["event_id"])

def to_bindings_list(b_dict):
    return [b_dict[e_id] for e_id in sorted(b_dict.keys())]
    

def model_enabled(model,state,transition):
        enabled = True
        for a in transition.in_arcs:
            if a.source not in state.keys():
                enabled = False
            elif len(state[a.source]) < 1:
                enabled = False
        return enabled

def powerset(iterable):
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(1,len(s)+1))

def combinations_without_repetitions(l,k):
    results = []
    for i in range(1,k+1):
        results+= list(itertools.combinations(l,i))
    return list(set(results))
    
def convertToNumber(s):
    return int.from_bytes(s.encode(), 'little')
def convert_place_to_number(p):
    return convertToNumber(p.name)
def convert_object_to_number(o):
    return convertToNumber(o[0]+str(o[1]))
def place_compare(p1,p2):
    if convertToNumber(p1.name) > convertToNumber(p2.name):
        return 1
    elif convertToNumber(p1.name) < convertToNumber(p2.name):
        return -1
    else:
        return 0

def state_to_string(state):
    s = ""
    k = sorted(list(state.keys()),key = convert_place_to_number)
    for key in k:
        s+=key.name
        s+=",".join([c[0]+","+str(c[1]) for c in state[key]])
    return s

def no_prefix_loop(prefixes):
    return not any([len(p) != len(set(p)) for p in prefixes.values()])

def state_to_place_counter(state):
    result = Counter()
    for p in state.keys():
        result+= Counter({p.name:len(state[p])})
    return hash(tuple(sorted(result.items())))

def binding_possible(ocpn,state,binding,object_types):
    if len(binding) == 0:
        return False
    tokens = [o for ot in object_types for o in binding[0][1][ot]]
    input_places_tokens = []
    t = None
    for t_ in ocpn.transitions:
        if t_.name == binding[0][0]:
            t = t_
    if t == None:
        return False
    for a in t.in_arcs:
        input_places_tokens += state[a.source] if a.source in state.keys() else []
    if set(tokens).issubset(set(input_places_tokens)) or set(tokens) == set(input_places_tokens):
        if model_enabled(ocpn,state,t):
            return True
    return False

def calculate_next_states_on_bindings(ocpn, state, binding, object_types):
    state_update_pairs = []
    
    if binding_possible(ocpn,state,binding,object_types):
        t = None
        for t_ in ocpn.transitions:
            if t_.name == binding[0][0]:
                t = t_
        in_places = {}
        out_places = {}
        for ot in object_types:
            in_places[ot] = [(x,y) for (x,y) in [(a.source,a.variable) for a in t.in_arcs] if x.object_type == ot]
            out_places[ot] = [x for x in [a.target for a in t.out_arcs] if x.object_type == ot]
        new_state = {k:state[k].copy() for k in state.keys()}
        update = not t.silent
        for ot in object_types:
            if ot not in binding[0][1].keys():
                continue
            for out_pl in out_places[ot]:
                if out_pl not in new_state.keys():
                    new_state[out_pl] = []
                new_state[out_pl]+=list(binding[0][1][ot])
            
            for (in_pl,is_v) in in_places[ot]:
                new_state[in_pl] = list((Counter(new_state[in_pl]) - Counter(list(binding[0][1][ot]))).elements())
                if new_state[in_pl] == []:
                    del new_state[in_pl]
            state_update_pairs.append((new_state,update))
        
    else:
        for t in ocpn.transitions:
            if t.silent:
                if model_enabled(ocpn,state,t):
                    input_tokens = {ot:[] for ot in object_types}
                    input_token_combinations = {ot:[] for ot in object_types}
                    in_places = {}
                    out_places = {}
                    for ot in object_types:
                        in_places[ot] = [(x,y) for (x,y) in [(a.source,a.variable) for a in t.in_arcs] if x.object_type == ot]
                        out_places[ot] = [x for x in [a.target for a in t.out_arcs] if x.object_type == ot]
                        token_lists = [[z for z in state[x]] for (x,y) in in_places[ot]]
                        #is_variable = any(y for (x,y) in in_places[ot])
                        if len(token_lists) != 0:
                            input_tokens[ot] = set.intersection(*map(set,token_lists))
                            input_token_combinations[ot] = list(combinations(input_tokens[ot], 1)) #if not is_variable else list(powerset_combinations(input_tokens[ot],prefixes)))#list(powerset_combinations(input_tokens[ot],prefixes)))
                        else:
                            input_tokens[ot] = set()
                    indices_list = [list(range(len(input_token_combinations[ot]))) if len(input_token_combinations[ot]) != 0 else [-1] for ot in object_types]
                    possible_combinations = list(product(*indices_list))
                    for comb in possible_combinations:
                        binding_silent = {}
                        for i in range(len(object_types)):
                            ot = object_types[i]
                            if -1 == comb[i]:
                                continue
                            binding_silent[ot] = input_token_combinations[ot][comb[i]]
                        new_state = {k:state[k].copy() for k in state.keys()}
                        update = not t.silent
                        for ot in object_types:
                            if ot not in binding_silent.keys():
                                continue
                            for out_pl in out_places[ot]:
                                if out_pl not in new_state.keys():
                                    new_state[out_pl] = []
                                new_state[out_pl]+=list(binding_silent[ot])
                            for (in_pl,is_v) in in_places[ot]:
                                new_state[in_pl] = list((Counter(new_state[in_pl]) - Counter(list(binding_silent[ot]))).elements())
                                if new_state[in_pl] == []:
                                    del new_state[in_pl]
                        state_update_pairs.append((new_state,update))
    return state_update_pairs

def update_binding(binding,update):
    if update:
        return copy.deepcopy(binding[1:])
    else:
        return copy.deepcopy(binding)





def enabled_log_activities(ocel,contexts):
    context_mapping = {}
    log_contexts = {}
    for index, event in ocel.iterrows():
        context = context_to_string(contexts[event["event_id"]])
        if context not in log_contexts.keys():
            log_contexts[context] = [index]
            context_mapping[context] = contexts[event["event_id"]]
        else:
            log_contexts[context].append(index)
    en_l = {}
    for context in log_contexts.keys():
        event_ids = log_contexts[context]
        en_l[context] = []
        for e in event_ids:
            en_l[context].append(ocel.at[e,"event_activity"])
        en_l[context] = list(set(en_l[context]))           
    return en_l

def enabled_model_activities(contexts,bindings,ocpn,object_types):
    print("Calculating en_m ....")
    results = {}
    times = [0,0,0,0,0,0]
    counter_e = 0
    for i in contexts.keys():#range(0,len(contexts)):
        if counter_e%250 == 0:
            print("event "+str(i) +" calculated "+str(counter_e))
        counter_e += 1
        context = contexts[i] 
        binding = bindings[i]
        q = []
        state_binding_set = set()
        initial_node = [{},binding]
        all_objects = {}
        for ot in object_types:
            all_objects[ot] = set()
            for b in binding:
                for o in b[1][ot]:
                    all_objects[ot].add((ot,o))
        for color in context.keys():
            
            tokens = all_objects[color]
            #if tokens ar enot in the bindings but the context indicates that they should be in the inital place they need to be added
            to_be_added = 0
            if len(tokens) != len(list(context[color].elements())):
                to_be_added = len(list(context[color].elements())) - len(tokens)
               
            if tokens == set() and to_be_added == 0:
                continue
            for p in ocpn.places:
                if p.object_type == color and p.initial:
                    #add START Tokens for each prefix a new token with new id
                    initial_node[0][p] = []
                    for (ot,o) in tokens:
                        initial_node[0][p].append((ot,o))
                    for i in range(0,to_be_added):
                        initial_node[0][p].append((ot,"additional"+str(i)))
                        
        initial_node = [initial_node]
        #transform bindings such that objects are identified as ot o not only o
        for b in binding:
            for ot in object_types:
                b[1][ot] = [(ot,o) for o in b[1][ot]]
        [q.append(node)for node in initial_node]
        index = 0
        context_string_target = context_to_string(context)
        if context_string_target not in results.keys():
            results[context_string_target] = set()
        [state_binding_set.add((state_to_place_counter(elem[0]),len(elem[1]))) for elem in q]
        while not index == len(q):
            elem = q[index]
            index+=1
            if len(elem[1]) == 0:
                for t in ocpn.transitions:
                    if model_enabled(ocpn,elem[0],t) and not t.silent:
                        results[context_string_target].add(t.name)
            t = time.time()  
            state_update_pairs = calculate_next_states_on_bindings(ocpn, elem[0], elem[1], object_types)
            times[1]+= time.time()-t 
            #for all next states
            for (state, update) in state_update_pairs:
                t = time.time() 
                updated_binding = update_binding(elem[1],update)
                times[3]+= time.time()-t 
                t = time.time()
                traditional_state_string = state_to_place_counter(state)
                times[2]+= time.time()-t 
                t = time.time() 
                if (traditional_state_string,len(updated_binding)) in state_binding_set:
                    continue
                state_binding_set.add((traditional_state_string,len(updated_binding)))
                q.append([state,updated_binding])
        del q   
        gc.collect()     
    return results

def calculate_precision_and_fitness(ocel,context_mapping,en_l,en_m):
    prec = []
    fit = []
    skipped = 0
    for index, row in ocel.iterrows():
        e_id = row["event_id"]
        context = context_mapping[e_id]
        en_l_a = en_l[context_to_string(context)]
        en_m_a = en_m[context_to_string(context)]
        if len(en_m[context_to_string(context)]) == 0 or (set(en_l_a).intersection(en_m_a) == set()):
            skipped+=1
            fit.append(0)
            continue
        prec.append(len(set(en_l[context_to_string(context)]).intersection(set(en_m[context_to_string(context)])))/float(len(en_m[context_to_string(context)])))
        fit.append(len(set(en_l[context_to_string(context)]).intersection(set(en_m[context_to_string(context)])))/float(len(en_l[context_to_string(context)])))
    return sum(prec)/len(prec), skipped, sum(fit)/len(fit)
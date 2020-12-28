"""
### FINAL PROJECT - the Wumpus World - CISC6525 Fall 2020
### Written by Yihao Li 
### 12/01/2020

### This code designs the agent to intelligently pick the next action in the
### Wumpus World. Specifically:
  1. Agent will pick a 100% safe move from its current position if it exists
  2. If there's no such move, agent will try to kill the Wumpus if it knows 
     the Wumpus' location and also the location is 100% free from a pit
  3. Agent will pick the safest move if former two are not available
  4. If gold is reachable, and agent isn't killed because of step 3 above,
     then agent will eventually grab it, climb out, and win the game
  5. If gold isn't reachable, and agent isn't killed because of step 3 above,
     then agent will climb out safely without the gold
  6. Agent always identifies the safety of edge cells (cells that could be 
     accessed from the been-to cells) as early as possible given percepts
     
### This code is modified from wwagent.py that only do random motions, 
### provided by the CISC6525 class. This code should work with the 
### wwsim.py provided by Greg Scott’s Github (gregscott94)


### Here are the new variables and functions I added for agent.
### Comprehensive comment could be found among the code
  ## New/Revised variables
    self.__WumpusAlive      self.__arrow
    self.__kb_w             self.__kb_p
    self.__model_w          self.__model_p
    self.__beento           self.__edge            
    self.__route            self.__hunt
    self.__climbout         
    self.__stopTheAgent --> self.__HaveGold
  ## New/Revised functions
    self.calculateArrowPosition(action)
    self.find_adj_cells(c_c)
    self.isTrue(prop, model)
    self.gen_nkb(okb, ps, new_s)
    self.update_kb_model()
    self.model_pos(symbols, model, KB, qry)
    self.model_pos_wp(symbols, model, KB, qry)
    self.flatten(nest_iter)
    self.check_pit(self, cell)
    self.check_wumpus(cell)
    self.search_route(start, goal)
    self.cal_action(current_goal, act_type)
    self.action()

### Notice:
  1. Comments start with at least two pound signs (##).
  2. Sentences start with only one pound sign (#) are commented code lines.
"""

from random import randint

## This is the class that represents an agent

class WWAgent:

    def __init__(self):
        self.__max=4                    ## number of cells in one side of square world
        self.__HaveGold = False         ## REVISED - True if having gold (was self.__stopTheAgent)
        self.__position = (0, 3)        ## upper left corner is (0,0)
        self.__directions = ['up','right','down','left']
        self.__facing = 'right'
        self.__percepts = (None, None, None, None, None)
        self.__map = [[ self.__percepts for i in range(self.__max) ] for j in range(self.__max)]
        self.__WumpusAlive = True       ## NEW - Wumpus alive or not
        self.__arrow = 1                ## NEW - arrow availiable or not
        self.__kb_w = ['not', 'w03']    ## NEW - knowledge base for Wumpus related information
        self.__kb_p = ['not', 'p03']    ## NEW - knowledge base for store pit information
        self.__model_w = {'w03':False}  ## NEW - model for Wumpus related information
        self.__model_p = {'p03':False}  ## NEW - model for pit related information
        self.__beento = []              ## NEW - all cells that agent has already been to
        self.__edge = []                ## NEW - all accessible cells that agent hasn't been to
        self.__route = []               ## NEW - the planned route, also the moving plan
        self.__hunt = []                ## NEW - the hunting plan (the Wumpus cell)
        self.__climbout = False         ## NEW - the exiting plan (True if activated)
        print("New agent created")


    #### self.update(percept)
    ## Add the latest percepts to list of percepts received so far
    ## This function is called by the wumpus simulation and will
    ## update the sensory data. The sensor data is placed into a
    ## map structured KB for later use    
    def update(self, percept):
        self.__percepts=percept
        #[stench, breeze, glitter, bump, scream]
        if self.__position[0] in range(self.__max) and self.__position[1] in range(self.__max):
            # new_p = tuple([i if i is not None else False for i in self.__percepts])
            self.__map[ self.__position[0]][self.__position[1]] = self.__percepts
        # puts the percept at the spot in the map where sensed


    #### self.calculateNextPosition(action)
    ## Since there is no percept for location, the agent has to predict
    ## what location it is in based on the direction it was facing
    ## when it moved
    def calculateNextPosition(self, action):
        if self.__facing=='up':
            self.__position = (self.__position[0],max(0,self.__position[1]-1))
        elif self.__facing =='down':
            self.__position = (self.__position[0],min(self.__max-1,self.__position[1]+1))
        elif self.__facing =='right':
            self.__position = (min(self.__max-1,self.__position[0]+1),self.__position[1])
        elif self.__facing =='left':
            self.__position = (max(0,self.__position[0]-1),self.__position[1])
        return self.__position


    #### self.calculateNextDirection(action)
    ## And the same is true for the direction the agent is facing, it also
    ## needs to be calculated based on whether the agent turned left/right
    ## and what direction it was facing when it did
    def calculateNextDirection(self, action):
        if self.__facing=='up':
            if action=='left':
                self.__facing = 'left'
            elif action=='right':
                self.__facing = 'right'
        elif self.__facing=='down':
            if action=='left':
                self.__facing = 'right'
            elif action=='right':
                self.__facing = 'left'
        elif self.__facing=='right':
            if action=='left':
                self.__facing = 'up'
            elif action=='right':
                self.__facing = 'down'
        elif self.__facing=='left':
            if action=='left':
                self.__facing = 'down'
            elif action=='right':
                self.__facing = 'up'
                
                
    ###NEW### self.calculateArrowPosition(action)
    ## A variation of self.calculateNextPosition(action)
    ## Calculate where the arrow goes
    def calculateArrowPosition(self, action):
        if self.__facing=='up':
            ap = (self.__position[0],max(0,self.__position[1]-1))
        elif self.__facing =='down':
            ap = (self.__position[0],min(self.__max-1,self.__position[1]+1))
        elif self.__facing =='right':
            ap = (min(self.__max-1,self.__position[0]+1),self.__position[1])
        elif self.__facing =='left':
            ap = (max(0,self.__position[0]-1),self.__position[1])
        return ap
        
    
    ###NEW### self.find_adj_cells(c_c = '')
    ## Generate a tuple of all adjacent cells given the current cell
    ## c_c (current cell) must be given as a string of x and y coordinate, e.g., "xy"
    ## If c_c is not given, will use self.__position to generate current cell
    def find_adj_cells(self, c_c = ''):
        if c_c:
            x, y = int(c_c[0]), int(c_c[1])
        else:
            x, y = self.__position[0], self.__position[1]
        temp_list, adj_cells = [], []
        temp_list.append(str(x)+str(min(self.__max-1,y+1)))
        temp_list.append(str(max(0,x-1))+str(y))
        temp_list.append(str(x)+str(max(0,y-1)))
        temp_list.append(str(min(self.__max-1,x+1))+str(y))
        for cell in temp_list:
            if cell != str(x)+str(y):
                adj_cells.append(cell)
        return tuple(adj_cells)

    
    ###NEW### self.isTrue(prop, model)
    ## Recursive function that checks whether a set of propositional logic sentences (prop)
    ## is True or False given the provided semantics (model)
    ## model is a dictionary using symbols as keys and storing the True/False in value
    ## e.g., model = {"p1":True, "p2":False, "p3":False}
    ## prop represents logic sentences in the form of a nested list, prop can be either a query
    ## or a knowledge base
    ## e.g., prop = [[[["not", "p1"], "and", "p2"]], "and", ["p2", "implies", "p3"]]
    def isTrue(self,prop,model):
        if isinstance(prop,str):
            if prop in model:
                return model[prop]
            else:
                return False
        elif len(prop)==1:
            return self.isTrue(prop[0],model)
        elif prop[0]=='not':
            return not self.isTrue(prop[1],model)
        elif prop[1]=='and':
            return self.isTrue(prop[0],model) and self.isTrue(prop[2],model)
        elif prop[1]=='or':
            return self.isTrue(prop[0],model) or self.isTrue(prop[2],model)
        elif prop[1]=='implies':
            return (not self.isTrue(prop[0],model)) or self.isTrue(prop[2],model)
        elif prop[1]=='iff':
            left = (not self.isTrue(prop[0],model)) or self.isTrue(prop[2],model)
            right= (not self.isTrue(prop[2],model)) or self.isTrue(prop[0],model)
            return (left and right)
        return False
        
        
    ###NEW### self.gen_nkb(okb, ps, new_s)
    ## Add a new sentence to current knowledge base and return the new KB
    ## The form of a knowledge base is the same as that of a prop in self.isTrue(prop, model)
    def gen_nkb(self, okb, ps, new_s):
        return [okb] + [ps, new_s]


    ###NEW### self.update_kb_model()
    ## Knowledge should be recorded whenever the agent goes into a new cell
    ## This function update the status of the Wumpus (alive or not) and record
    ## the sentences and semantics about wumpus, pit, stench, and breeze of 
    ## the current cell and adjacent cells
    ## The form of a knowledge base is the same as that of a prop in self.isTrue(prop, model)
    ## The form of a model is the same as that of a model in self.isTrue(prop, model)
    def update_kb_model(self):
        current_position = str(self.__position[0])+str(self.__position[1])
        adj_cells = self.find_adj_cells()
        ## Update if Wumpus alive or not
        if self.__percepts[4] == "scream":
            self.__WumpusAlive = False
            print("Great! Wumpus killed!")
        ## Update the knowledge base and model for pit and breeze
        if "p"+current_position not in self.__model_p:
            self.__model_p["p"+current_position] = False
            self.__kb_p = self.gen_nkb(self.__kb_p, 'and' , ['not', "p"+current_position])
        if "b"+current_position not in self.__model_p:
            breeze = True if self.__percepts[1] == 'breeze' else False
            self.__model_p["b"+current_position] = breeze
            if breeze:  ## if breeze in cell, pit exists in at least one of the adjacent cells
                l_o = "p"+adj_cells[0]
                for cell in adj_cells[1:]:
                    l_o = self.gen_nkb(l_o, 'or' , "p"+cell)
                new_prop_p = self.gen_nkb("b"+current_position, 'implies', l_o)
                self.__kb_p = self.gen_nkb(self.__kb_p, 'and' , new_prop_p)
            if not breeze:  ## if breeze not in cell, all adjacent cells are safe from pits
                for cell in adj_cells:
                    if "p"+cell not in self.__model_p:
                        self.__model_p["p"+cell] = False
                        self.__kb_p = self.gen_nkb(self.__kb_p, 'and' , ['not', "p"+cell])
        ## Update the knowledge base and model for Wumpus and stench (ONLY when Wumpus is still ALIVE)
        if self.__WumpusAlive:
            if "w"+current_position not in self.__model_w:
                self.__model_w["w"+current_position] = False
                self.__kb_w = self.gen_nkb(self.__kb_p, 'and' , ['not', "w"+current_position])
            if "s"+current_position not in self.__model_w:
                stench = True if self.__percepts[0] == 'stench' else False
                self.__model_w["s"+current_position] = stench
                if stench:  ## if stench in cell, Wumpus exists in at least one of the adjacent cells
                    l_o = "w"+adj_cells[0]
                    for cell in adj_cells[1:]:
                        l_o = self.gen_nkb(l_o, 'or' , "w"+cell)
                    new_prop_w = self.gen_nkb("s"+current_position, 'implies', l_o)
                    self.__kb_w = self.gen_nkb(self.__kb_w, 'and' , new_prop_w)
                if not stench:  ## if stench not in cell, all adjacent cells are safe from Wumpus
                    for cell in adj_cells:
                        if "w"+cell not in self.__model_w:
                            self.__model_w["w"+cell] = False
                            self.__kb_w = self.gen_nkb(self.__kb_w, 'and' , ['not', "w"+cell])
                            

    ###NEW### self.model_pos(symbols, model, KB, qry)
    ## Check if a knowledge base (KB) entails a query (qry) by model enumeration
    ## Returns the P (probability) of the qry being True under the circumstances 
    ## that the KB is True, given all the possible models
    ## If returns P = 1, KB entails qry
    ## If returns P < 1, KB does not entail qry
    ## If returns P = 0, KB entails (not qry)
    ## The form of KB and qry are the same as that of a prop in self.isTrue(prop, model)
    ## model stores all the known semantics 
    ## symbols is a list of symbols with unknown semantics to be enumerated    
    def model_pos(self,symbols,model,KB,qry):
        n_k = n_a = 0
        def modelcheck(symbols,model,KB,qry):  ## Recursively enumerate symbols and generate all possible models
            nonlocal n_k, n_a
            if len(symbols)==0:
                if self.isTrue(KB,model):  ## Check if KB is Ture under one model
                    n_k += 1
                    if self.isTrue(qry,model):  ## Check if qry is Ture under the same model
                        n_a += 1
                return
            else:
                p = symbols[0]
                rest = list(symbols[1:len(symbols)])
                temp_t, temp_f = model.copy(), model.copy()
                temp_t.update({p:True})
                temp_f.update({p:False})
                modelcheck(rest,temp_t,KB,qry)
                modelcheck(rest,temp_f,KB,qry)
                return
        modelcheck(symbols,model,KB,qry)
        if n_k > 0:
            p_value = n_a/n_k
        else:  ## If KB is False in all models, considers that KB entails qry
            p_value = 1.0
        return round(p_value,4)
    
    
    ###NEW### self.model_pos_wp(symbols, model, KB, qry)
    ## A variation of self.model_pos(symbols,model,KB,qry) customized for Wumpus
    ## Since the Wumpus exists in one and only one cell, the enumeration method
    ## is changed in this function
    def model_pos_wp(self,symbols,model,KB,qry):
        n_k = n_a = 0
        for sb in symbols:
            ## All other symbols are set to be False at a time except for only
            ## one symbol
            new_dict = {esb:False for esb in symbols}
            new_dict[sb] = True
            new_model = dict(model)
            new_model.update(new_dict)
            if self.isTrue(KB,new_model):
                n_k += 1
                if self.isTrue(qry,new_model):
                    n_a += 1
        if n_k > 0:
            p_value = n_a/n_k
        else:
            p_value = 1.0
        return round(p_value,4)
    
    
    ###NEW### self.flatten(nest_iter)
    ## Flatten a nested list/tuple by yielding all items if it is not a list or tuple
    ## This function makes it easier for us to find needed symbols from a KB
    ## P.S. 
    ## Repalce "(list,tuple)" with "Iterable" in the 3rd line if you need to 
    ## deal with more types of iterable objects. If you want to do so, remember 
    ## to import the needed library by "from collections import Iterable"
    def flatten(self, nest_iter):
        for x in nest_iter:
            if isinstance(x, (list,tuple)) and not isinstance(x, (str, bytes)):
                yield from self.flatten(x)
            else:
                yield x
    
    
    ###NEW### self.check_pit(cell)
    ## Use pit related knowledge base (self.__kb_p) and model (self.__model_p) to generate
    ## the P (probability) of a given cell being free from a pit
    ## Besides, update self.__kb_p and self.__model_p when a pit is certain to exist (P=0)
    ## or not exist (P=1) in that cell
    def check_pit(self, cell):
        if "p"+cell in self.__model_p:  ## Retrieve information from model if it's already there
            p_no_pit = 0.0 if self.__model_p["p"+cell] else 1.0
        else:  ## Get information by reasoning otherwise
            KB = list(self.__kb_p)
            model = self.__model_p.copy()
            qry = ['not', 'p'+cell]
            op_set = set(['not', 'and', 'or', 'implies', 'iff'])
            all_symbols = set(self.flatten(KB))-op_set  ## Get the symbols that exist in the KB yet
            symbols = []                                ## not in the model to be enumerated
            for sb in all_symbols:
                if not sb in model:
                    symbols.append(sb)
            p_no_pit = self.model_pos(symbols, model, KB, qry)
            if p_no_pit == 1.0:
                self.__model_p["p"+cell] = False
                self.__kb_p = self.gen_nkb(self.__kb_p, 'and' , ['not', "p"+cell])
            if p_no_pit == 0.0:
                self.__model_p["p"+cell] = True
                self.__kb_p = self.gen_nkb(self.__kb_p, 'and' , "p"+cell)
        return p_no_pit
    
    
    ###NEW### self.check_wumpus(cell)
    ## Use Wumpus related knowledge base (self.__kb_w) and model (self.__model_w) to generate
    ## the P (probability) of a given cell being free from Wumpus
    ## Besides, update self.__kb_w and self.__model_w when Wumpus is certain to exist (P=0)
    ## or not exist (P=1) in that cell
    def ckeck_wumpus(self, cell):
        if "w"+cell in self.__model_w:  ## Retrieve information from model if it's already there
            p_no_wumpus = 0.0 if self.__model_w["w"+cell] else 1.0
        else:  ## Get information by reasoning otherwise
            all_cells = set(['w'+str(i)+str(j) for i in range(self.__max) for j in range(self.__max)])
            un_rec_cells = all_cells - set(self.__model_w.keys())
            rec_cells = all_cells - un_rec_cells
            wp_already_found = False
            for rec_cell in rec_cells:
                wp_already_found = self.__model_w[rec_cell] or wp_already_found
            if wp_already_found:  ## If Wumpus exsits in known recorded cells, it cannot exist in unrecorded cells 
                p_no_wumpus = 1.0
            else:  ## If Wumpus doesn't exsit in known recorded cells, then do the model enumeration
                symbols = list(un_rec_cells)
                KB = list(self.__kb_w)
                model = self.__model_w.copy()
                qry = ['not', 'w'+cell]
                p_no_wumpus = self.model_pos_wp(symbols,model,KB,qry)
            if p_no_wumpus == 1.0:
                self.__model_w["w"+cell] = False
                self.__kb_w = self.gen_nkb(self.__kb_w, 'and' , ['not', "w"+cell])
            if p_no_wumpus == 0.0:
                self.__model_w["w"+cell] = True
                self.__kb_w = self.gen_nkb(self.__kb_w, 'and' , "w"+cell)
        return p_no_wumpus

    
    ###NEW### self.search_route(start, goal)
    ## Search a best route (least actions) from the starting cell (start) to the goal cell (goal)
    ## A variation of UCS (uniform cost search). The step cost is 2 when requiring a turn, otherwise 1
    ## Route given with a list of cells (from the next cell to the goal cell)
    ## All the cells must be selected from self.__beento (meaning it's safe) except for the goal cell
    def search_route(self,start,goal):
        fringe = [[start, 0, []]]
        rubbish = list()  ## A list of already seached cells
        safe_cells = list(self.__beento) + [goal]
        while len(fringe) > 0:
            rootnode, rootcost = fringe[0], fringe[0][1]
            for node in fringe:  ## Search for the node with least cost to expand
                if node[1] < rootcost:
                    rootnode = node
            fringe.remove(rootnode)  ## Remove the node that will be expanded
            root = rootnode[0]
            if root == goal:                  ## If this node end with the goal, then it's the required route
                return rootnode[2][1:]+[goal] ## Return this route (excluding the starting cell)
            next_cell_list = []
            for cell in self.find_adj_cells(root):  ## Search for possible next step
                if cell in safe_cells:              ## They should be safe of course
                    next_cell_list.append(cell)
            rubbish.append(root)  ## Record already searched cells
            last_cell = ""
            if rootnode[2]:
                last_cell = rootnode[2][-1]
            for cell in next_cell_list:
                if not cell in rootnode[2] and not cell in rubbish:  ## Prevent repeat or recursion
                    step_cost = 1  ## Default step cost is 1
                    if last_cell:
                        x0, y0 = int(cell[0]), int(cell[1])
                        x1, y1 = int(root[0]), int(root[1])
                        x2, y2 = int(last_cell[0]), int(last_cell[1])
                        ## If an extra turn required, the step cost should be 2 instead of 1
                        if not ((x0==x1 and x0==x2) or (y0==y1 and y0==y2)):  
                            step_cost = 2
                    newnode = [cell, rootnode[1]+step_cost, rootnode[2]+[root]] # expand the path by one cell
                    fringe.append(newnode)  ## Put new nodes at the end
        return []  ## Retuen empty list if there is no possible route
    
    
    ###NEW### self.cal_action(current_goal, act_type)
    ## Given current cell, current direction, and adjacent cell, calculate and 
    ## return the next action to move/shoot into that adjacent cell
    ## act_type should be "move" or "shoot", defaulted to be "move"
    def cal_action(self, current_goal, act_type='move'):
        def cal_facing(facing):  ## Function to represent 4 directions as orthogonal unit vectors
            fc = (-1,0) if facing == "left" else ((1,0) if facing == "right" else ((0,1) if facing == "up" else ((0,-1) if facing == "down" else "")))
            return fc
        x_diff, y_diff = int(current_goal[0]) - self.__position[0], int(current_goal[1]) - self.__position[1]
        if x_diff == -1 and y_diff == 0:
            needed_facing = "left"
        if x_diff == 1 and y_diff == 0:
            needed_facing = "right"
        if x_diff == 0 and y_diff == -1:
            needed_facing = "up"
        if x_diff == 0 and y_diff == 1:
            needed_facing = "down"
        needed_facing = cal_facing(needed_facing)  ## Represent 4 directions as orthogonal unit vectors
        current_facing = cal_facing(self.__facing)
        ## Judge whether a turn is needed / what direction of turn is needed 
        ## by dot product and cross product of current_facing and needed_facing
        dot_p = current_facing[0]*needed_facing[0] + current_facing[1]*needed_facing[1]
        cross_p = current_facing[0]*needed_facing[1] - needed_facing[0]*current_facing[1]
        if dot_p == 1:                      ## If no turn is needed, "move" or "shoot"
            action = act_type
        elif dot_p == 0 and cross_p == -1:  ## If a right turn is needed, "right"
            action = 'right'
        else:                               ## Otherwise, "left"
            action = 'left'
        return action
    
    
    ##REVISED## self.action()
    ## Actions: 'left', 'right', 'move', 'grab', 'shoot', 'climb', 'exit'
    ## This function is revised to intelligently pick the next action of the agent
    ## 1. Agent will pick a 100% safe move from its current position if it exists
    ## 2. If there's no such move, agent will try to kill the Wumpus if it knows the
    ##    Wumpus' location and also the location is 100% free from a pit
    ## 3. Agent will pick the safest move if former two are not available
    ## 4. If gold is reachable, and agent isn't killed because of step 3 above, then 
    ##    agent will eventually grab it, climb out, and win the game
    ## 5. If gold isn't reachable, and agent isn't killed because of step 3 above,
    ##    then agent will climb out safely without the gold
    ## 6. Agent always identifies the safety of edge cells (cells that could be 
    ##    accessed from the been-to cells) as early as possible given percepts
    def action(self):
        current_position = str(self.__position[0])+str(self.__position[1])  ## Get current position
        ## Step 0.1
        ## Grab the gold (if not already)
        if ('glitter' in self.__percepts) and (not self.__HaveGold):
            print("Agent will grab the gold!")
            self.__HaveGold = True  ## Having the gold! Work is over !!!
            return 'grab'
        ## Step 0.2
        ## Generate the route to climb out if agent has got the gold
        if self.__HaveGold and not self.__climbout:
            self.__climbout = True  ## Now activate the plan to climb out
            self.__route = self.search_route(current_position, '03')
        
        ## Step 1.
        ## Delete the first goal in self.__route if current position is 
        ## the first goal (so the agent could move on to the next one)
        if len(self.__route) > 0:
            if current_position == self.__route[0]:
                self.__route = list(self.__route[1:])
                
        ## Step 2.
        ## If the agent doesn't have a plan currently, which means that the agent
        ## is in a new cell or it just killed the Wumpus, the agent need to update 
        ## KBs and models. Then agent will make a new plan based on new information
        if len(self.__route) == 0 and len(self.__hunt) == 0 and not self.__climbout:
            
            ## Step 2.1 
            ## Update the knowledge bases and models
            self.update_kb_model()
            ## Remove current position from self.__edge
            for edge_cell in list(self.__edge):
                if current_position in edge_cell:
                    self.__edge.remove(edge_cell)
                    break
            ## Add current position to self.__beento
            if not current_position in self.__beento:
                self.__beento.append(current_position)
            
            ## Step 2.2 
            ## Add adjecent cells to self.__edge if they are not in self.__beento 
            ## and not in self.__edge
            adj_cells = self.find_adj_cells()
            for cell in adj_cells:
                if not cell in self.__beento:
                    if not cell in set(self.flatten(self.__edge)):
                        self.__edge.append((cell, (None, None, None)))
            
            ## Step 2.3
            ## Update the probability of being safe for every cell in self.__edge
            ## in the form of a tuple - (cell, (p_safe, p_np, p_nw))
            ## p_safe is the P of being safe (free from both pits and wumpus) 
            ## p_np/p_nw are the P of free from pits/wumpus
            for idx, p_x in enumerate(self.__edge):
                cell = p_x[0]
                p_np = self.check_pit(cell)  ## Calculate p_np
                if self.__WumpusAlive:       ## Wumpus alive, calculate p_nw
                    p_nw = self.ckeck_wumpus(cell)
                else:                        ## Wumpus dead, set p_nw = 1
                    p_nw = 1.0
                self.__edge[idx] = (cell, (p_np, p_nw, p_np*p_nw))
            ## Then rank the cells in self.__edge by p_safe ascendingly
            self.__edge = sorted(self.__edge, key = lambda p_x: p_x[-1][-1])     
            
            ## Step 2.4
            ## Now get a new plan !!!
            temp_dest = ""  ## A temporary destination 
            p_lg = self.__edge[-1][-1][-1]  ## The largest p_safe so far
            
            ## Step 2.4.1
            ## If the largest p_safe < 1, check whether the Wumpus is good to be
            ## killed. We only do so when we know the certain cell and the cell
            ## does not have a pit in it
            if p_lg < 1:
                if self.__WumpusAlive and self.__arrow>0:
                    cell_W = ""
                    for p_x in self.__edge:
                        if (p_x[-1][1] == 0) and (p_x[-1][0] == 1):
                            cell_W = p_x[0]
                            break
                    ## If such a cell exits, set the temp_dest to be that cell
                    ## Also add that cell to the hunting plan (self.__hunt)
                    if cell_W:
                        self.__hunt = [cell_W]
                        temp_dest = cell_W
                        
            ## Step 2.4.2
            ## If not having a hunting plan, choose a safe cell (p_safe=1) or 
            ## the possibly safest cell (0<p_safe<1) as the temp_dest, or if 
            ## there are only unsafe cells (p_safe=0), make a plan to climb out
            if not self.__hunt:
                if p_lg > 0:  ## Choose the safest cell
                    temp_dest = self.__edge[-1][0]
                else:         ## Or plan to exit
                    temp_dest = "03"
                    self.__climbout = True  ## Activating the leaving plan

            ## Step 2.4.3
            ## Whatever the new plan is, search for a route to the temp_dest
            if temp_dest in adj_cells:
                self.__route = [temp_dest]
            else:
                self.__route = self.search_route(current_position, temp_dest)
            if self.__hunt:
                ## When hunting plan activated, delete the last cell of the
                ## route, since we don't want to face the Wumpus !!!
                self.__route = list(self.__route[:-1])
        
        ## Step 3. 
        ## Since we are having a plan now, calculate next action base on our plan
        ## 3.1 If we have a route now, go to the next cell
        if len(self.__route) > 0:
            current_goal = self.__route[0]
            action = self.cal_action(current_goal, 'move')
        ## 3.2 Otherwise if we have the hunting plan, shoot an arrow to the Wumpus
        elif len(self.__hunt) > 0:
            current_goal = self.__hunt[0]
            action = self.cal_action(current_goal, 'shoot')
        ## 3.2 Otherwise we must want to exit !!!
        else:
            if self.__HaveGold:
                print("\nAgent has won this episode!\n")
            else:
                print("\nGold is not reachable! Agent is climbing out!\n")
            return "climb"
        
        ## Step 4. 
        ## Calculate new position/direction/arrow status basing on action
        ## Print out action and new status of the agent (recommend to only
        ## print these when running the GUI mode).
        if action == 'shoot':
            self.__arrow = 0
            self.__hunt = []
            # ap = self.calculateArrowPosition(action)
            # print (f"Agent shoot an arrow to ({ap[1]},{ap[0]}):", "--> current status:", f"({self.__position[1]}, {self.__position[0]})", self.__facing)
        if action == 'move':
            self.calculateNextPosition(action)
            # print ("Agent action:", action , "forward --> current status:", f"({self.__position[1]},{self.__position[0]})", self.__facing)
        if action == 'left' or action == 'right':
            self.calculateNextDirection(action)
            # print ("Agent action: turn", action , "--> current status:", f"({self.__position[1]},{self.__position[0]})", self.__facing)

        return action
Display #1: Overview -  Each turn, side by side, focusing on law, tech, ruler, and wonder timings
Tech Start - Icon of the tech, with a smaller, secondary icon in the corner of the tech icon of type (science, training, law, order). Hover for text.
-Science techs: Centralization, Architecture, Monasticism, Land Consolidation, Portcullis, Scholarship, Cartography, Metaphysics, Hydraulics
-Training techs: Military Drill, Composite Bow, Sovereignty
-Law techs: Rhetoric, Labor Force, Aristocracy, Sovereignty, Navigation, Monasticism, Citizenship, Doctrine, Architecture, Manor, Vaulting, Martial Code, Jurisprudence, Lanteen Sail, Fiscal Policy
-Order techs: Navigation, Jurisprudence, Citizenship, Monasticism, Doctrine
Law enacted/swapped -  Icon of the law, with secondary icon in the corner of the law icon (order, training, science, goods, rushing), previous law <-> swapped law if there was a law swap. Icon of the of the UU unlocked if this is the 4th or 7th law enacted after the law tech. Hover for text. Unsure if minor training laws should be included.
-Science Laws (beaker): Centralization, Exploration (according to Klass), Constitution, Philosophy
-Training Laws (training): Major - Tyranny. Lesser -  Iconography, Professional Army, Volunteers.
-Order Laws (order scroll): Serfdom, Monotheism, Divine Rule, Coin Debasement, Elites
-Resource Laws (goods icon, or specific resource icon if you want): Slavery, Vassalage, Tyranny, Legal Code, Engineering, Autarky
-Rushing Laws (swift icon?): Orthodoxy, Volunteers
Mil Unit/Building Unlocked - Icon of the unit/building. For example, on the turn that Military Drill finishes, have a barracks icon.
Ruler Archetype Icon on each turn -  with a red X over it the turn it died and some icon to denote a new one. The game must store the rulers to populate the Succession screen, does that means traits on each turn are known, or just at death?
-Would be great if mouseover of ruler icon showed traits, but if we only have that as a state at current turn (so death or now, then exclude).
Wonder started - Icon of wonder with worker cooldown: building icon over it.
Wonder finished - Icon of wonder with something denoting finished. Unsure if any logic let's us note a wonder getting canceled, but we'd love that on this timeline if possible too.
City founded - Generic icon for most cities or, better, the family icon. Hover for city name. Different icon for Capital, and possibly family seats as well.
City development level increases above weak - Unsure what logic to use here. We care about first access to a Wonder, the ability to rush, and ability to build UUs. But I don't think we're that interested in this for every city, just too spammy. Maybe first instance of each unique culture level greater than weak. Such that we'd see on timeline first developing culture, first strong culture, first legendary culture. We don't need anything past that imo.
Battles - Presumably we have total strength/turn for every turn to populate the existing final turn graph of that. If that's the case, a decrease in military strength can be interpreted as a unit loss, and a % loss of (tbd) in military strength could be used to place a battle marker.
Tech Unit received.

Display #2 - Relative Resources
Total Order Count per turn (patched soon :filthyLove: Solver)
Orders being used on improvements
Orders available for military moves Presumably 2+3 can be calcultaed from the "soon-to-be-patched" save variables. Order count on the turns battles occur is really powerful for understanding outcomes.
Raw Science per turn. Be nice to have this as comparative as well. Such that on t22 player 1 was making 15% more science/turn than player
Accumulated Tech (Total science produced - total science spent on one-time use cards). I don't think this number, as a raw number, is very useful for players. It'd be nice if it could be expressed in some way that let the conclusion be "Player 1 is 1.5 techs ahead of Player 2". Tech cost scaling is what makes that tricky, but maybe some approximation based on turn count, or something similar might work.
Resource totals Again, I suspect we want both raw and relative.
Resource values? We have price/resource at each turn, and raw count of each resource. Value of those resources might be useful, either as unique stats or for a "player's total wealth" stat or both.
Solvers message (below) means we could do training and civics / turn as absolute and relative too.

Feels like some small summary of Display #2 would be useful in Display #1. I'm imagining #2 being a new tab/page, and the larger icons of #1 having a smaller grid on each turn with |p1+|p2++|=| and a few categories possibly the ones that the game tells players on each turn. Maybe relative military strength, relative accumulated science, relative military orders. But using our new calculated categories. So each turn at a glance would show p1 has more military strength, player 2 has much more accumulated science (not counting tech cards) and they're about equal in orders available to be spent on this turn. P1 and P2 could be their nation icon.

